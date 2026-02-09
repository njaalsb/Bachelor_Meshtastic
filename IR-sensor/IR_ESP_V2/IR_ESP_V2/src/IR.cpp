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

// sjekk bit 0 i status reg for å avgjøre om interface er busy
bool IR::busy_bit(){
    
    int reg = 0x02;
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
    std::vector<int> resultat = IR::int_to_bits(state);
    
    
    IR::print_vec(resultat);
    return resultat[0]==1;
}

// Funksjon for å hente registerinnhold basert på verdi motatt
std::vector<int> IR::int_to_bits(int input){
    std::vector<int> vec;
    
    // Loop through all 16 bits (or 8 if you want byte-only)
    for(int i = 0; i < 16; i++){  // Fixed: use constant, not vec.size()
        vec.push_back((input >> i) & 1);
    }    
    return vec;
}

void IR::print_vec(std::vector<int> input){
    for(int i = 0; i < input.size(); i++){
        Serial.print(input[i]);
    }
    Serial.println("");
}

void IR::sync(void){
    int i;
    int data = 0x0f;

    // Steg 1. Deassert CS and idle SCK
    digitalWrite(SPI_CS, HIGH);
    delay(200); // Antar at et blokkerende delay vil stoppe SCK

    IR::read_vospi_packet(packet_buffer);


    

    while ((data & 0x0f) == 0x0f){
        // Asserter CS
        digitalWrite(SPI_CS, LOW);
        data = SPI.transfer(0x00) << 8;
        data |= SPI.transfer(0x00);
        digitalWrite(SPI_CS, HIGH);
        
        if(!IR::is_discard_packet(packet_buffer)){
            Serial.println("Synkronisering fullført");
        }

        for (i = 0; i < ((VOSPI_PACKET_SIZE - 2) / 2); i++) {
            digitalWrite(SPI_CS, LOW);
            SPI.transfer(0x00);
            SPI.transfer(0x00);
            digitalWrite(SPI_CS, HIGH);
        }
    }
}

// Sjekker etter discard packet, discard viss pakkenummeret er 0xF
bool IR::is_discard_packet(byte* packet){
    uint16_t packet_id = (packet[0] << 8) | packet[1];
    return (packet_id & 0x0F00) == 0x0F00;
}

// CS må settes lav før denne funksjonen kalles
void IR::read_vospi_packet(byte* packet){
    for (int i = 0; i < VOSPI_PACKET_SIZE; i++){
        packet[i] = SPI.transfer(0x00);
    }
}