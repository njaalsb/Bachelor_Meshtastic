#pragma once 

#include "Wire.h"

// I2C addresse:
#define ADDRESSE (0x2A)

// Pins: 
#define SPI_MOSI    23
#define SPI_MISO    19
#define SPI_SCK     18
#define SPI_CS      5
#define I2C_SDA     21
#define I2C_SCL     22
#define RESET_PIN   4

class IR {
    private:

    public:
        void I2C_connect(void);
        void boot(void);    
        int read_stat();
        int read_power();
};
