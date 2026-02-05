#pragma once 

#include "Wire.h"
#include "SPI.h"
#include <vector>
#include <iostream>

// I2C addresse:
#define ADDRESSE (0x2A)

// ESP32 Pins: 
#define SPI_MOSI    23
#define SPI_MISO    19
#define SPI_SCK     18
#define SPI_CS      5
#define I2C_SDA     21
#define I2C_SCL     22
#define RESET_PIN   4

class IR {
    private:
        void boot(void);

    public:
        IR() = default;
        void I2C_connect(void);
        int read_stat();
        int read_power();
        void sync();
        bool busy_bit();   
        std::vector<int> int_to_byte(int input);
};
