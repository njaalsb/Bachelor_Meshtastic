#include <QApplication>
#include <QThread>
#include <QMutex>
#include <QColor>
#include <QtDebug>
#include <QString>
#include <QTimer>
#include <QDateTime>
#include <QBuffer>
#include <QRandomGenerator>
#include <QtEndian>

#include "LeptonThread.h"
#include "MeshtasticHelper.h"
#include "SDRThread.h"
#include "ImageSendThread.h"

void printUsage(char *cmd) {
    char *cmdname = basename(cmd);
    printf("Usage: %s [OPTION]...\n"
           " -h       display this help and exit\n"
           " -cm x    select colormap\n"
           "            1 : rainbow\n"
           "            2 : grayscale\n"
           "            3 : ironblack [default]\n"
           " -tl x    select type of Lepton\n"
           "            2 : Lepton 2.x [default]\n"
           "            3 : Lepton 3.x\n"
           " -ss x    SPI bus speed [MHz] (10 - 30)\n"
           "            20 : 20MHz [default]\n"
           " -min x   override minimum value for scaling (0 - 65535)\n"
           " -max x   override maximum value for scaling (0 - 65535)\n"
           " -d x     log level (0-255)\n"
           " -sdr_enable   enable SDR monitoring\n"
           " -sdr_freq x   SDR center frequency in Hz [default 869525000]\n"
           " -sdr_thresh x  SDR signal threshold [default 10000.0]\n"
           "", cmdname, cmdname);
}

int main(int argc, char **argv)
{
    int typeColormap = 3;
    int typeLepton   = 2;
    int spiSpeed     = 20;
    int rangeMin     = -1;
    int rangeMax     = -1;
    int loglevel     = 0;
    bool sdrEnable   = false;
    uint32_t sdrFreq = 869525000;
    float sdrThresh  = 10000.0f;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-h") == 0) {
            printUsage(argv[0]);
            exit(0);
        }
        else if (strcmp(argv[i], "-d") == 0) {
            int val = 3;
            if ((i + 1 != argc) && (strncmp(argv[i+1], "-", 1) != 0)) {
                val = std::atoi(argv[i+1]); i++;
            }
            if (0 <= val) loglevel = val & 0xFF;
        }
        else if ((strcmp(argv[i], "-cm") == 0) && (i + 1 != argc)) {
            typeColormap = std::atoi(argv[i+1]); i++;
        }
        else if ((strcmp(argv[i], "-tl") == 0) && (i + 1 != argc)) {
            typeLepton = std::atoi(argv[i+1]); i++;
        }
        else if ((strcmp(argv[i], "-ss") == 0) && (i + 1 != argc)) {
            spiSpeed = std::atoi(argv[i+1]); i++;
        }
        else if ((strcmp(argv[i], "-min") == 0) && (i + 1 != argc)) {
            rangeMin = std::atoi(argv[i+1]); i++;
        }
        else if ((strcmp(argv[i], "-max") == 0) && (i + 1 != argc)) {
            rangeMax = std::atoi(argv[i+1]); i++;
        }
        else if (strcmp(argv[i], "-sdr_enable") == 0) {
            sdrEnable = true;
        }
        else if ((strcmp(argv[i], "-sdr_freq") == 0) && (i + 1 != argc)) {
            sdrFreq = (uint32_t)std::atoll(argv[i+1]); i++;
        }
        else if ((strcmp(argv[i], "-sdr_thresh") == 0) && (i + 1 != argc)) {
            sdrThresh = std::atof(argv[i+1]); i++;
        }
    }

    QApplication a(argc, argv);

    // --- Lepton camera thread ---
    LeptonThread *leptonThread = new LeptonThread();
    leptonThread->setLogLevel(loglevel);
    leptonThread->useColormap(typeColormap);
    leptonThread->useLepton(typeLepton);
    leptonThread->useSpiSpeedMhz(spiSpeed);
    leptonThread->setAutomaticScalingRange();
    if (0 <= rangeMin) leptonThread->useRangeMinValue(rangeMin);
    if (0 <= rangeMax) leptonThread->useRangeMaxValue(rangeMax);

    // Keep a thread-safe copy of the latest frame
    QImage lastImage;
    QMutex imageMutex;
    QObject::connect(leptonThread, &LeptonThread::updateImage, [&](QImage image) {
        QMutexLocker lock(&imageMutex);
        lastImage = image.copy();
    });
    leptonThread->start();

    // --- Image send thread ---
    ImageSendThread *sendThread = new ImageSendThread();

    QObject::connect(sendThread, &ImageSendThread::chunkSent, [](int idx, int total) {
        qDebug() << "[main] Chunk sent:" << idx << "/" << (total - 1);
    });
    QObject::connect(sendThread, &ImageSendThread::sendComplete, []() {
        qDebug() << "[main] Image fully sent.";
    });
    QObject::connect(sendThread, &ImageSendThread::sendSkipped, []() {
        qDebug() << "[main] Frame skipped (previous send still in progress).";
    });


    // If the send thread is still busy from the last image it will skip. Trying with 120 seconds
    QTimer *captureTimer = new QTimer();
    QObject::connect(captureTimer, &QTimer::timeout, [&]() {
        QImage image;
        {
            QMutexLocker lock(&imageMutex);
            if (lastImage.isNull()) {
                qDebug() << "[main] No frame available yet, skipping.";
                return;
            }
            image = lastImage.copy();
        }

        // Compress to WebP off the main thread would be ideal, but the
        // QBuffer operation is fast enough here (<5ms for 160x120).
        QByteArray buffer;
        QBuffer buf(&buffer);
        buf.open(QIODevice::WriteOnly);
        image.save(&buf, "WEBP", 40); //Q is the quality factor (0-100), lower is more compression
        buf.close();

        qDebug() << "[main] Compressed image:" << buffer.size()
                 << "bytes ->" << ((buffer.size() + 149) / 150) << "chunks";

        // Save a local backup
        QString filename = QString("thermal_backup_%1.webp")
                               .arg(QDateTime::currentDateTime()
                                        .toString("yyyy-MM-dd_hh-mm-ss"));
        if (image.save(filename, "WEBP", 40)) {
            qDebug() << "[main] Saved local backup:" << filename;
        }

        // Hand off to send thread (non-blocking)
        sendThread->sendImage(buffer);
    });

    captureTimer->start(120000);

    // --- SDR thread can be enabled ---
    if (sdrEnable) {
        SDRThread *sdrThread = new SDRThread();
        sdrThread->setFrequency(sdrFreq);
        sdrThread->setThreshold(sdrThresh);
        QObject::connect(sdrThread, &SDRThread::signalUpdate, [](float power) {
            QString alert = QString("SDR|ALERT|%1").arg(power);
            MeshtasticHelper::instance().sendMessage(alert);
        });
        sdrThread->start();
    }

    MeshtasticHelper::instance().sendMessage("Proof of concept code is starting");

    return a.exec();
}