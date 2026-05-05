#include "ImageSendThread.h"
#include "MeshtasticBridge.h"

#include <QMutexLocker>
#include <QRandomGenerator>
#include <QtEndian>
#include <QDebug>

ImageSendThread::ImageSendThread(QObject *parent)
    : QThread(parent) {}

void ImageSendThread::sendImage(const QByteArray &webpData)
{
    QMutexLocker lock(&m_mutex);
    if (m_busy) {
        emit sendSkipped();
        return;
    }
    m_pending = webpData;
    m_busy = true;
    lock.unlock();

    if (!isRunning())
        start();
}

void ImageSendThread::run()
{
    while (true) {
        QByteArray buffer;
        {
            QMutexLocker lock(&m_mutex);
            if (!m_busy || m_pending.isEmpty()) {
                m_busy = false;
                return;
            }
            buffer = m_pending;
            m_pending.clear();
        }

        const int total = (buffer.size() + MAX_PAYLOAD - 1) / MAX_PAYLOAD;
        const quint8 sid = (quint8)QRandomGenerator::global()->bounded(1, 256);

        qDebug() << "sid=" << sid << "chunks=" << total << "bytes=" << buffer.size();

        for (int idx = 0; idx < total; idx++) {
            QByteArray payload = buffer.mid(idx * MAX_PAYLOAD, MAX_PAYLOAD);

            QByteArray packet(8, 0);
            packet[0] = (char)PACKET_TYPE_IMG;
            packet[1] = (char)sid;
            qToBigEndian((quint16)total,        (uchar*)packet.data() + 2);
            qToBigEndian((quint16)idx,           (uchar*)packet.data() + 4);
            qToBigEndian((quint16)payload.size(),(uchar*)packet.data() + 6);
            packet.append(payload);

            MeshtasticBridge::instance().sendRawData(packet, PORTNUM_ATAK_FORWARDER);
            emit chunkSent(idx, total);

            if (idx < total - 1)
                QThread::msleep(CHUNK_DELAY_MS);
        }

        emit sendComplete();
        qDebug() << "Done! sid=" << sid;

        QMutexLocker lock(&m_mutex);
        if (m_pending.isEmpty()) {
            m_busy = false;
            return;
        }
    }
}