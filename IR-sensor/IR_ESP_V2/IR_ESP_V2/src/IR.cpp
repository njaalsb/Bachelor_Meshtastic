#include "IR.h"

// I2C addresse:
#define ADDRESSE (0x2A)

// Addresser:
#define status (0x0002)

// Pins: 
#define SPI_MOSI    23
#define SPI_MISO    19
#define SPI_SCK     18
#define SPI_CS      5
#define I2C_SDA     21
#define I2C_SCL     22
#define RESET_PIN   4

void I2C_connect(void){
    uint16_t stat;

    pinMode(RESET_PIN, OUTPUT);

    Serial.println("Reebooter kamera");

    // 5 sekund fra boot til I2C interfacen kan brukes 
    digitalWrite(RESET_PIN, LOW);

    delay(100);
    
    digitalWrite(RESET_PIN, HIGH);
    
    delay(10000);

    // Oppretter kontakt med kamera:
    Wire.begin(I2C_SDA, I2C_SCL);

    Serial.println("Reset fullført");

    stat = Wire.read();

    Wire.requestFrom(ADDRESSE, status);

    

    Serial.println(stat);
}

void start_up(void){
    ;;
}