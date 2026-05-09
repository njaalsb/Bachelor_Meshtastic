#ifndef IMAGESENDTHREAD_H
#define IMAGESENDTHREAD_H

#include <QThread>
#include <QByteArray>
#include <QMutex>

class ImageSendThread : public QThread
{
    Q_OBJECT
public:
    explicit ImageSendThread(QObject *parent = nullptr);
    void sendImage(const QByteArray &webpData);

protected:
    void run() override;

signals:
    void chunkSent(int idx, int total);
    void sendComplete();
    void sendSkipped();

private:
    QByteArray  m_pending;
    QMutex      m_mutex;
    bool        m_busy = false;

    static constexpr int MAX_PAYLOAD     = 226;
    static constexpr int CHUNK_DELAY_MS  = 3000;
    static constexpr int PORTNUM_ATAK_FORWARDER = 257;
    static constexpr quint8 PACKET_TYPE_IMG = 0x02;
};

#endif // IMAGESENDTHREAD_H