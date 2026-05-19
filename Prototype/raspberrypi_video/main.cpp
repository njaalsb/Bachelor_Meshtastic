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
#include "MeshtasticBridge.h"
#include "ImageSendThread.h"

int main(int argc, char **argv)
{
    int typeColormap = 2;
    int typeLepton   = 3;
    int spiSpeed     = 20;
    int rangeMin     = -1;
    int rangeMax     = -1;
    int loglevel     = 0;

    QApplication a(argc, argv);

    LeptonThread *leptonThread = new LeptonThread();
    leptonThread->setLogLevel(loglevel);
    leptonThread->useColormap(typeColormap);
    leptonThread->useLepton(typeLepton);
    leptonThread->useSpiSpeedMhz(spiSpeed);
    leptonThread->setAutomaticScalingRange();
    if (0 <= rangeMin) leptonThread->useRangeMinValue(rangeMin);
    if (0 <= rangeMax) leptonThread->useRangeMaxValue(rangeMax);

    QImage lastImage;
    QMutex imageMutex;
    QObject::connect(leptonThread, &LeptonThread::updateImage, [&](QImage image) {
        QMutexLocker lock(&imageMutex);
        lastImage = image.copy();
    });
    leptonThread->start();

    ImageSendThread *sendThread = new ImageSendThread();
    QObject::connect(sendThread, &ImageSendThread::chunkSent, [](int idx, int total) {
        qDebug() << "chunk" << idx << "/" << (total - 1);
    });
    QObject::connect(sendThread, &ImageSendThread::sendComplete, []() {
        qDebug() << "Done";
    });
    QObject::connect(sendThread, &ImageSendThread::sendSkipped, []() {
        qDebug() << "Frame skipped, thread busy";
    });

    QTimer *captureTimer = new QTimer();
    QObject::connect(captureTimer, &QTimer::timeout, [&]() {
        QImage image;
        {
            QMutexLocker lock(&imageMutex);
            if (lastImage.isNull()) {
                qDebug() << "No frame yet";
                return;
            }
            image = lastImage.copy();
        }

        QByteArray buffer;
        QBuffer buf(&buffer);
        buf.open(QIODevice::WriteOnly);
        image.save(&buf, "WEBP", 40);
        buf.close();

        qDebug() << "Compressed" << buffer.size() << "bytes ->" << ((buffer.size() + 200) / 200) << "chunks";

        sendThread->sendImage(buffer);
    });

    captureTimer->start(300000);

    MeshtasticBridge::instance().sendMessage("test");
    return a.exec();
}