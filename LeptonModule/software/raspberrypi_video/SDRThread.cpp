#include "SDRThread.h"
#include <rtl-sdr.h>
#include <iostream>
#include <cmath>
#include <unistd.h>

SDRThread::SDRThread() : QThread()
{
    frequency = 869525000; // 100 MHz default
    threshold = 10000.0f; // default threshold
    running = true;
    dev = NULL;
    maxPower = 0.0f;
    counter = 0;
}

SDRThread::~SDRThread() {
    running = false;
    if (dev) {
        rtlsdr_close(dev);
    }
}

void SDRThread::setFrequency(uint32_t freq)
{
    frequency = freq;
}

void SDRThread::setThreshold(float thresh)
{
    threshold = thresh;
}

void SDRThread::run()
{
    int r = rtlsdr_open(&dev, 0);
    if (r < 0) {
        std::cerr << "Failed to open rtl-sdr device" << std::endl;
        return;
    }

    rtlsdr_set_center_freq(dev, frequency);
    rtlsdr_set_sample_rate(dev, 2048000); // 2.048 MS/s
    rtlsdr_set_tuner_gain_mode(dev, 0); // auto gain
    rtlsdr_reset_buffer(dev);

    const int buffer_size = 1024 * 2; // IQ samples
    uint8_t buffer[buffer_size];

    while (running) {
        int n_read;
        r = rtlsdr_read_sync(dev, buffer, buffer_size, &n_read);
        if (r < 0) {
            std::cerr << "Read error" << std::endl;
            continue;
        }
        if (n_read > 0) {
            float power = 0.0f;
            for (int i = 0; i < n_read; i += 2) {
                float I = buffer[i] - 127.5f;
                float Q = buffer[i+1] - 127.5f;
                power += I * I + Q * Q;
            }
            power /= (n_read / 2); // average power

            maxPower = std::max(maxPower, power);
            counter++;
            if (counter >= 300) {
                emit signalUpdate(maxPower);
                maxPower = 0.0f;
                counter = 0;
            }
        }
        usleep(100000); // 100ms delay
    }
}