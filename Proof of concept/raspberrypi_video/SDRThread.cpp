#include "SDRThread.h"
#include <rtl-sdr.h>
#include <iostream>
#include <cmath>
#include <unistd.h>
#include <complex>
#include <vector>

SDRThread::SDRThread() : QThread()
{
    frequency  = 869525000;
    threshold  = 10000.0f;
    running    = true;
    dev        = nullptr;
    peakFreqHz = 0.0f;
    counter    = 0;
}

SDRThread::~SDRThread() {
    running = false;
    if (dev) rtlsdr_close(dev);
}

void SDRThread::setFrequency(uint32_t freq) { frequency = freq; }
void SDRThread::setThreshold(float thresh)  { threshold = thresh; }

float SDRThread::computePeakFreq(const uint8_t *buf, int len)
{
    int N = len / 2; // number of IQ pairs
    std::vector<std::complex<float>> samples(N);

    for (int i = 0; i < N; i++) {
        float I = buf[i * 2]     - 127.5f;
        float Q = buf[i * 2 + 1] - 127.5f;
        samples[i] = {I, Q};
    }

    // Remove DC (like: samples = samples - np.mean(samples))
    std::complex<float> mean(0, 0);
    for (auto &s : samples) mean += s;
    mean /= N;
    for (auto &s : samples) s -= mean;

    // FFT (Cooley-Tukey, in-place)
    for (int s = 1; s < N; s <<= 1) {
        for (int i = 0; i < N; i += s << 1) {
            for (int j = 0; j < s; j++) {
                float angle = -M_PI * j / s;
                std::complex<float> w(std::cos(angle), std::sin(angle));
                std::complex<float> u = samples[i + j];
                std::complex<float> t = w * samples[i + j + s];
                samples[i + j]     = u + t;
                samples[i + j + s] = u - t;
            }
        }
    }

    // fftshift + power
    std::vector<float> power(N);
    for (int i = 0; i < N; i++) {
        int shifted = (i + N / 2) % N;
        power[i] = std::abs(samples[shifted]);
    }

    // Zero out DC (like: power[mid-20:mid+20] = 0)
    int mid = N / 2;
    for (int i = mid - 20; i <= mid + 20; i++)
        power[i] = 0.0f;

    // Find peak
    int peakBin = 0;
    float peakPow = 0.0f;
    for (int i = 0; i < N; i++) {
        if (power[i] > peakPow) {
            peakPow = power[i];
            peakBin = i;
        }
    }

    // Convert to Hz
    float freqOffset = (peakBin - N / 2) * (2048000.0f / N);
    return static_cast<float>(frequency) + freqOffset;
}

void SDRThread::run()
{
    int r = rtlsdr_open(&dev, 0);
    if (r < 0) {
        std::cerr << "Failed to open rtl-sdr device" << std::endl;
        return;
    }

    rtlsdr_set_center_freq(dev, frequency);
    rtlsdr_set_sample_rate(dev, 2048000);
    rtlsdr_set_tuner_gain_mode(dev, 0);
    rtlsdr_reset_buffer(dev);

    
    const int NUM_SAMPLES = 256 * 1024;
    const int BUFFER_SIZE = NUM_SAMPLES * 2; // IQ pairs
    std::vector<uint8_t> buffer(BUFFER_SIZE);

    // 600 * 100ms = 60 seconds
    const int Timer = 600;

    while (running) {
        int n_read = 0;
        r = rtlsdr_read_sync(dev, buffer.data(), BUFFER_SIZE, &n_read);
        if (r < 0 || n_read <= 0) {
            usleep(100000);
            continue;
        }

        float freqHz = computePeakFreq(buffer.data(), n_read);

        // Track the reading from the most recent sample each iteration,
        // emit once per minute
        peakFreqHz = freqHz;
        counter++;
        if (counter >= Timer) {
            emit signalUpdate(peakFreqHz);
            counter = 0;
        }

        usleep(100000);
    }
}