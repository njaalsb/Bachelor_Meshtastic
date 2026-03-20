#ifndef SDRTHREAD_H
#define SDRTHREAD_H

#include <QThread>
#include <QtCore>

struct rtlsdr_dev;

class SDRThread : public QThread
{
    Q_OBJECT;

public:
    SDRThread();
    ~SDRThread();

    void setFrequency(uint32_t freq);
    void setThreshold(float thresh);
    void run();

signals:
    void signalUpdate(float maxPower);

private:
    uint32_t frequency;
    float threshold;
    bool running;
    rtlsdr_dev *dev;

    float maxPower;
    int counter;
};

#endif // SDRTHREAD_H