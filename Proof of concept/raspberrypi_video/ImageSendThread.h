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

    // Call this to queue a new image for sending.
    // If a send is already in progress it will be skipped.
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

    static constexpr int MAX_PAYLOAD  = 150;  // bytes per chunk (well under 230 limit)
    static constexpr int CHUNK_DELAY_MS = 10000; // 10 seconds between chunks
};

#endif // IMAGESENDTHREAD_H