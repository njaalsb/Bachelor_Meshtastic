#include <QApplication>
#include <QThread>
#include <QMutex>
#include <QMessageBox>
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
           "                [for your reference] Please use nice command\n"
           "                 e.g. sudo nice -n 0 ./%s -tl 3\n"
           " -ss x    SPI bus speed [MHz] (10 - 30)\n"
           "            20 : 20MHz [default]\n"
           " -min x   override minimum value for scaling (0 - 65535)\n"
           "            [default] automatic scaling range adjustment\n"
           "            e.g. -min 30000\n"
           " -max x   override maximum value for scaling (0 - 65535)\n"
           "            [default] automatic scaling range adjustment\n"
           "            e.g. -max 32000\n"
           " -d x     log level (0-255)\n"
           " -sdr_enable   enable SDR monitoring\n"
           " -sdr_freq x   SDR center frequency in Hz [default 869525000]\n"
           " -sdr_thresh x  SDR signal threshold [default 10000.0]\n"
           "", cmdname, cmdname);
}

int main( int argc, char **argv )
{
    int typeColormap = 3; // Default to Ironblack for proper thermal look
    int typeLepton = 2; 
    int spiSpeed = 20; 
    int rangeMin = -1; 
    int rangeMax = -1; 
    int loglevel = 0;
    bool sdrEnable = false;
    uint32_t sdrFreq = 869525000; 
    float sdrThresh = 10000.0f;

    for(int i=1; i < argc; i++) {
        if (strcmp(argv[i], "-h") == 0) {
            printUsage(argv[0]);
            exit(0);
        }
        else if (strcmp(argv[i], "-d") == 0) {
            int val = 3;
            if ((i + 1 != argc) && (strncmp(argv[i + 1], "-", 1) != 0)) {
                val = std::atoi(argv[i + 1]);
                i++;
            }
            if (0 <= val) loglevel = val & 0xFF;
        }
        else if ((strcmp(argv[i], "-cm") == 0) && (i + 1 != argc)) {
            typeColormap = std::atoi(argv[i + 1]);
            i++;
        }
        else if ((strcmp(argv[i], "-tl") == 0) && (i + 1 != argc)) {
            typeLepton = std::atoi(argv[i + 1]);
            i++;
        }
        else if ((strcmp(argv[i], "-ss") == 0) && (i + 1 != argc)) {
            spiSpeed = std::atoi(argv[i + 1]);
            i++;
        }
        else if ((strcmp(argv[i], "-min") == 0) && (i + 1 != argc)) {
            rangeMin = std::atoi(argv[i + 1]);
            i++;
        }
        else if ((strcmp(argv[i], "-max") == 0) && (i + 1 != argc)) {
            rangeMax = std::atoi(argv[i + 1]);
            i++;
        }
        else if (strcmp(argv[i], "-sdr_enable") == 0) {
            sdrEnable = true;
        }
        else if ((strcmp(argv[i], "-sdr_freq") == 0) && (i + 1 != argc)) {
            sdrFreq = (uint32_t)std::atoll(argv[i + 1]);
            i++;
        }
        else if ((strcmp(argv[i], "-sdr_thresh") == 0) && (i + 1 != argc)) {
            sdrThresh = std::atof(argv[i + 1]);
            i++;
        }
    }

    QApplication a( argc, argv );
    QImage lastImage;

    LeptonThread *thread = new LeptonThread();
    thread->setLogLevel(loglevel);
    thread->useColormap(typeColormap);
    thread->useLepton(typeLepton);
    thread->useSpiSpeedMhz(spiSpeed);
    thread->setAutomaticScalingRange();
    if (0 <= rangeMin) thread->useRangeMinValue(rangeMin);
    if (0 <= rangeMax) thread->useRangeMaxValue(rangeMax);
    
    // Connect the thread to our local storage variable
    // .copy() ensures we get the COLORED version of the frame
    QObject::connect(thread, &LeptonThread::updateImage, [&](QImage image) {
        lastImage = image.copy();
    });
    
    thread->start();
    
    QTimer *saveTimer = new QTimer();
    QObject::connect(saveTimer, &QTimer::timeout, [&]() {
        if (!lastImage.isNull()) {
            qDebug() << "Preparing thermal image for mesh...";
                                   
            QByteArray buffer;
            QBuffer buf(&buffer);
            buf.open(QIODevice::WriteOnly);
            
            lastImage.save(&buf, "WEBP", 40); 
            buf.close();
            
            int maxPayload = 200; 
            int total = (buffer.size() + maxPayload - 1) / maxPayload;
            quint8 sid = QRandomGenerator::global()->bounded(1, 256);
            
            qDebug() << "Total chunks:" << total << "sid:" << sid;
            
            for(int idx = 0; idx < total; idx++) {
                QByteArray payload = buffer.mid(idx * maxPayload, maxPayload);
                
                // Create 7-byte binary header
                QByteArray packet(7, 0);
                packet[0] = (char)sid;
                qToBigEndian((quint16)total, (uchar*)packet.data() + 1);
                qToBigEndian((quint16)idx, (uchar*)packet.data() + 3);
                qToBigEndian((quint16)payload.size(), (uchar*)packet.data() + 5);

                packet.append(payload);
                
                // Base64 encode the combined binary (header + payload)
                QString packetB64 = QString(packet.toBase64());
                QString msg = QString("IMG|%1|%2|%3").arg(sid).arg(idx).arg(packetB64);
                
                MeshtasticHelper::instance().sendMessage(msg);
                
                qDebug() << "Sent chunk" << idx << "/" << (total-1);
                QThread::msleep(15000); 
            }
            
            // Save a high-quality color backup locally
            QString filename = QString("thermal_backup_%1.webp").arg(QDateTime::currentDateTime().toString("yyyy-MM-dd_hh-mm-ss"));
            if (lastImage.save(filename, "WEBP", 40)) {
                qDebug() << "Saved colored backup to disk:" << filename;
            }
        } 
    }); 
    
    saveTimer->start(30000); // Send an image every 30 seconds
    
    if (sdrEnable) {
        SDRThread *sdrThread = new SDRThread();
        sdrThread->setFrequency(sdrFreq);
        sdrThread->setThreshold(sdrThresh);
        QObject::connect(sdrThread, &SDRThread::signalUpdate, [&](float power) {
            QString alert = QString("SDR ALERT: Signal Power %1").arg(power);
            MeshtasticHelper::instance().sendMessage(alert);
        });
        sdrThread->start();
    }
    
    MeshtasticHelper::instance().sendMessage("Wiwowiwo");

    return a.exec();
}