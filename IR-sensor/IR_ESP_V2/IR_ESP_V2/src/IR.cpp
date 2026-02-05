#include "IR.h"

void IR::I2C_connect(void){
    uint16_t status;

    IR::boot();

    // Oppretter kontakt med kamera:
    Wire.begin(I2C_SDA, I2C_SCL);
    Wire.setClock(100000);

    status = IR::read_stat();

    Serial.print("Kameraets status er: ");
    Serial.println(status);

    // Dersom boot er mislykket looper vi her
    while(status == 0){
        Serial.println("Boot er ikke fullført");
        Serial.print("Status er: ");
        Serial.println(status);
        delay(500);
    }
}

int IR::read_stat(){  
    int reg = 0x2;
    int stat = 0;
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

int IR::read_power(){
    
    int stat = 0;
    int reg = 0x0;

    Wire.beginTransmission(ADDRESSE);

    Wire.write(reg >> 8 & 0xff);
    Wire.write(reg & 0xff);

    Wire.endTransmission(ADDRESSE);

    delayMicroseconds(100);

    // requester 2 byte fra kameraet
    Wire.requestFrom(ADDRESSE, 2);

    if(Wire.available() >= 2){
        stat = Wire.read() << 8;  // High byte
        stat |= Wire.read();       // Low byte
    }

    return stat;
}

void IR::boot(void){
    // Kamera boot sekvens
    digitalWrite(RESET_PIN, HIGH);

    delay(100);

    digitalWrite(RESET_PIN, LOW);

    Serial.println("Rebooter kamera");

    delay(100);
    
    digitalWrite(RESET_PIN, HIGH);
    
    // 5 sekund fra boot til I2C interfacen er tilgjengelig
    delay(5000);

    Serial.println("Reset fullført");
}

bool IR::busy_bit(){
    // sjekk bit 0 i status reg for å avgjøre om interface er busy
    std::vector<int> resultat;
    int reg = 0x02;
    char availability;
    int state;

    Wire.beginTransmission(ADDRESSE);

    Wire.write(reg >> 8 & 0xff);
    Wire.write(reg & 0xff);            // sends one byte

    Wire.endTransmission();

    Wire.requestFrom(ADDRESSE, 2);

    if(Wire.available() >= 2){
        state = Wire.read() << 8;  // High byte
        state = Wire.read();       // Low byte
    }

    resultat = IR::int_to_byte(state);
    return resultat[0];
}

std::vector<int> IR::int_to_byte(int input){
    char availability;
    availability = static_cast<char>(input);

    std::vector<int> vec;

    for(int i = 0; i < 8; i++){
        // vector emplace back something? 
        // Pakke det inn i funksjon etter hvert
        vec.emplace_back((availability >> i) & 1);
    }
    return vec;
}