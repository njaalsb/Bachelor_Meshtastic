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
<<<<<<< HEAD
};

=======
    float maxPower;
    int counter;
};
>>>>>>> 54fa8f525b2b419cc26975592d6e070db3a5c976

#endif // SDRTHREAD_H