#pragma once 

#include "Wire.h"
#include "SPI.h"
#include <vector>
#include <iostream>

// Kamera register 
#define ADDRESSE (0x2A) // I2C addresse

// Command ID register
#define AGC (0x01)      //
#define SYS (0x02)
#define VID (0x03)
#define OEM (0x08)


#define GET (0x00)
#define SET (0x01)
#define RUN (0x02)

// ESP32 Pins: 
#define SPI_MOSI    23
#define SPI_MISO    19
#define SPI_SCK     18
#define SPI_CS      5
#define I2C_SDA     21
#define I2C_SCL     22
#define RESET_PIN   4

#define I2C_CLK_FREQ 100000 // 100KHz I2C klokke

// Konfigurerer for RAW14-mode
#define IMAGE_WIDTH 80          // pixler
#define IMAGE_HEIGHT 60         // pixler
#define IMAGE_PAYLOAD 160       // bytes
#define VOSPI_PACKET_SIZE 164   // Bytes i en packet 4 byte header
#define VOSPI_FRAME_SIZE 4      // 4 stk
#define PACKETS_PER_SEGMENT 60  // 60 pakker per segment
#define SEGMENTS_PER_FRAME 4    // 4 segmenter per frame 

class IR {
    private:
        void boot(void);
    public:
        IR() = default;
        byte packet_buffer[VOSPI_PACKET_SIZE];
        void I2C_connect(void);
        int read_stat();
        int read_power();
        void sync();
        bool busy_bit();   
        std::vector<int> int_to_bits(int input);
        void print_vec(std::vector<int> input);
        void read_vospi_packet(byte* packet);
        void print_buffer(byte buffer[VOSPI_PACKET_SIZE]);
        bool is_discard_packet(byte* packet);
};
