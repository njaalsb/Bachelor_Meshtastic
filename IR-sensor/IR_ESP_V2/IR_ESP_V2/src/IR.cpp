#include "IR.h"

void IR::I2C_connect(void){
    uint16_t status;

    IR::boot();

    // Oppretter kontakt med kamera:
    Wire.begin(I2C_SDA, I2C_SCL);
    Wire.setClock(I2C_CLK_FREQ);

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

    Wire.write(reg >> 8 & 0xff); // For å sjekke kameraets status må vi lese status registeret (0x0002)
    Wire.write(reg & 0xff);      // dette må gjøres i to operasjoner siden addressen er 16-bits      

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
        stat = Wire.read() << 8;    // High byte
        stat |= Wire.read();        // Low byte
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

// Kalles ved startup eller når ting ikke er synkronisert
/*
void IR::sync(void){
    int data = 0x0F00;  // Inialiserer data som discard
    
    // deasserter CS og venter litt
    digitalWrite(SPI_CS, HIGH);
    delay(200);
    digitalWrite(SPI_CS, LOW);  // Asserter CS for å starte avlesning 
    
    // Fortsetter å lese helt til vi får en pakke som ikke er av discard typen 
    // (ikke 0x0F00 i headeren)
    while ((data & 0x0F00) == 0x0F00){
        data = SPI.transfer(0x00) << 8;
        data |= SPI.transfer(0x00);
        
        // Tømmer resterende 162 bytes for å sjekke neste header
        for (int i = 0; i < (VOSPI_PACKET_SIZE - 2); i++) {
            SPI.transfer(0x00);
        }
    }
    
    digitalWrite(SPI_CS, HIGH);
    Serial.println("Synkronisering fullført");
}*/

void IR::sync(void){
    // Robust VoSPI synchronization:
    // 1. Deassert CS and wait for frame period
    // 2. Assert CS and search for segment 1, packet 0
    // 3. Once found, we're synchronized
    
    digitalWrite(SPI_CS, HIGH);
    delay(200);  // Wait for frame period
    digitalWrite(SPI_CS, LOW);
    delayMicroseconds(10);
    
    Serial.println("VoSPI sync: Searching for segment 1...");
    
    int attempts = 0;
    int discard_count = 0;
    bool found_seg1 = false;
    
    // Read up to 300 packets looking for segment 1, packet 0
    for (int i = 0; i < 300; i++) {
        read_vospi_packet(packet_buffer);
        attempts++;
        
        if (is_discard_packet(packet_buffer)) {
            discard_count++;
            // After discards, next valid packets should be segment 1
            if (discard_count > 5) {
                Serial.println("  Found discard packets, waiting for segment 1...");
            }
            continue;
        }
        
        int seg = get_segment_number(packet_buffer);
        int pkt = get_packet_number(packet_buffer);
        
        // Found segment 1!
        if (seg == 1 && pkt >= 0 && pkt < 60) {
            Serial.printf("  SYNC SUCCESS: Found Seg 1, Pkt %d after %d packets\n", pkt, attempts);
            found_seg1 = true;
            break;
        }
    }
    
    digitalWrite(SPI_CS, HIGH);
    
    if (!found_seg1) {
        Serial.println("  WARNING: Sync incomplete, will retry next frame");
    }
    
    delay(100);
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

// Helper functions for packet parsing
int IR::get_segment_number(byte* packet){
    uint16_t header = (packet[0] << 8) | packet[1];
    return (header >> 12) & 0x7;
}

int IR::get_packet_number(byte* packet){
    uint16_t header = (packet[0] << 8) | packet[1];
    return header & 0xFF;
}

// Cursed og hardkodet funksjon
void IR::print_buffer(byte buffer[VOSPI_PACKET_SIZE]){
    Serial.println("===================VOSPI PACKET===========================");
    for(int i = 0; i < VOSPI_PACKET_SIZE; i++){  // Fixed: i += 4
        Serial.print(buffer[i]);
        Serial.print(",");  // Add space for readability
    }
    Serial.println("");
    Serial.println("END OF VOSPI PACKET");
}

void IR::set_freq_out(void){
    // Configure I2S to generate 25MHz clock on GPIO0 using APLL
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate = 25000000,  // 25MHz target
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 2,
        .dma_buf_len = 8,
        .use_apll = true,  // Enable APLL for precise frequency
        .tx_desc_auto_clear = true,
        .fixed_mclk = 0
    };

    i2s_pin_config_t pin_config = {
        .bck_io_num = FREQ_OUT,    // Bit clock output on GPIO0
        .ws_io_num = -1,            // No word select needed
        .data_out_num = -1,         // No data output needed
        .data_in_num = -1           // No data input needed
    };

    // Install and configure I2S driver
    i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_NUM_0, &pin_config);
    
    // Start I2S to begin clock output
    i2s_start(I2S_NUM_0);
    
    Serial.println("25MHz clock configured on GPIO0 using I2S with APLL");
}