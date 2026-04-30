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
        qDebug() << "[ImageSendThread] Still sending previous image, skipping this frame.";
        emit sendSkipped();
        return;
    }
    m_pending = webpData;
    m_busy    = true;
    lock.unlock();

    // Start the thread if not already running
    if (!isRunning()) {
        start();
    }
}

void ImageSendThread::run()
{
    while (true) {
        QByteArray buffer;
        {
            QMutexLocker lock(&m_mutex);
            if (!m_busy || m_pending.isEmpty()) {
                m_busy = false;
                return; // Nothing to do, exit thread
            }
            buffer  = m_pending;
            m_pending.clear();
        }

        const int total = (buffer.size() + MAX_PAYLOAD - 1) / MAX_PAYLOAD;
        const quint8 sid = (quint8)QRandomGenerator::global()->bounded(1, 256);

        qDebug() << "Sending image: sid=" << sid
                 << "chunks=" << total
                 << "bytes=" << buffer.size();

        for (int idx = 0; idx < total; idx++) {
            QByteArray payload = buffer.mid(idx * MAX_PAYLOAD, MAX_PAYLOAD);

            // 8-byte binary header: [0x02][sid:1][total:2][idx:2][plen:2]
            QByteArray packet(8, 0);
            packet[0] = (char)0x02;  // TRANSFER_TYPE_IMAGE
            packet[1] = (char)sid;
            qToBigEndian((quint16)total, (uchar*)packet.data() + 2);
            qToBigEndian((quint16)idx,   (uchar*)packet.data() + 4);
            qToBigEndian((quint16)payload.size(), (uchar*)packet.data() + 6);
            packet.append(payload);

            MeshtasticBridge::instance().sendRawData(packet, 257);  // 257 = ATAK_FORWARDER
            emit chunkSent(idx, total);

            qDebug() << "[ImageSendThread] Sent chunk" << idx << "/" << (total - 1);

            // Only sleep between chunks, not after the last one
            if (idx < total - 1) {
                QThread::msleep(CHUNK_DELAY_MS);
            }
        }

        emit sendComplete();
        qDebug() << "[ImageSendThread] Send complete for sid=" << sid;

        // Check if a new image was queued while we were sending
        QMutexLocker lock(&m_mutex);
        if (m_pending.isEmpty()) {
            m_busy = false;
            return;
        }
        // If there's a new pending image, loop and send it
    }
}