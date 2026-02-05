#include "IR.h"

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

void IR::I2C_connect(void){
    uint16_t status;
    
    // Kamera boot sekvens
    pinMode(RESET_PIN, OUTPUT);
     
    digitalWrite(RESET_PIN, HIGH);

    delay(100);

    digitalWrite(RESET_PIN, LOW);

    Serial.println("Rebooter kamera");

    delay(100);
    
    digitalWrite(RESET_PIN, HIGH);
    
    // 5 sekund fra boot til I2C interfacen er tilgjengelig
    delay(5000);

    Serial.println("Reset fullført");

    // Oppretter kontakt med kamera:
    Wire.begin(I2C_SDA, I2C_SCL);
    Wire.setClock(100000);

    

    status = IR::read_stat();

    Serial.print("Kameraets status er: ");
    Serial.println(status);
}

int IR::read_stat(){  
    int reg = 0x2;
    int stat = 69;
    byte error;
    // Velger hvilket register vi ønsker å hente data fra
    Wire.beginTransmission(ADDRESSE);

    //Wire.write(0x00);// For å sjekke kameraets status må vi lese status registeret (0x0002)
    //Wire.write(0x02);// dette må gjøres i to operasjoner siden addressen er 16-bits

    Wire.write(reg >> 8 & 0xff);
    Wire.write(reg & 0xff);            // sends one byte

    delayMicroseconds(500);
    error = Wire.endTransmission(true);

    if(error != 0){
        Serial.print("Feilmelding: ");
        Serial.println(error);
    }

    // requester 2 byte fra kameraet
    Wire.requestFrom(ADDRESSE, 2);

    if(Wire.available() >= 2){
        stat = Wire.read() << 8;  // High byte
        stat |= Wire.read();       // Low byte
    }

    return stat;
}

byte IR::read_power(){
    Wire.beginTransmission(ADDRESSE);
    byte stat = 0;

    Wire.write(0x00);
    Wire.write(0x00);
    Wire.endTransmission(ADDRESSE);
    delayMicroseconds(100);
    Wire.requestFrom(ADDRESSE, 1);

    if(Wire.available()){
        stat = Wire.read();
    }

    return stat;
}

void IR::start_up(void){
    ;;
}