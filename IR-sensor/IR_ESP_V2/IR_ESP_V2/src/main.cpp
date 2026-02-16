#include <Arduino.h>
#include "IR.h"
int var;
// Instansierer kameraet
IR cam;
bool busy;

void setup() {
    Serial.begin(115200);

    pinMode(RESET_PIN, OUTPUT);
    pinMode(SPI_CS, OUTPUT);
    
    cam.I2C_connect();

    SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI, SPI_CS);
    SPI.setDataMode(SPI_MODE3);
    SPI.setFrequency(10000000);  // 10 MHz SPI clock

    Serial.print("Status: ");
    Serial.println(cam.read_stat());
    busy = cam.busy_bit(); // Sjekker om I2C interface er klart 

    cam.sync(); // Synkroniserer
}

  // Test sekvens:
    /*
    * 1. Booter kamera
    * 2. Kobler på I2C
    * 3. Leser statusregister
    * 4. Starter SPI
    * 5. Sjekker BUSY bit
    * 6. Etablerer SYNC 
    * 7. Print buffer (som forhåpentligvis er stappbuff av bra data!)
    */
    

void loop() {
    static int frame_count = 0;
    static int resync_count = 0;
    
    // Start frame read: CS HIGH, wait for frame period, then CS LOW
    digitalWrite(SPI_CS, HIGH);
    delay(185);  // Wait >185ms for frame period
    digitalWrite(SPI_CS, LOW);
    delayMicroseconds(10);
    
    // Track packets in this frame read
    int packets_read = 0;
    int valid_packets = 0;
    int discard_packets = 0;
    int seg1_count = 0, seg2_count = 0, seg3_count = 0, seg4_count = 0;
    
    // Read continuously for up to 500 packets
    for (int i = 0; i < 500; i++) {
        cam.read_vospi_packet(cam.packet_buffer);
        packets_read++;
        
        // Parse header
        uint16_t header = (cam.packet_buffer[0] << 8) | cam.packet_buffer[1];
        int segment = (header >> 12) & 0x7;
        int packet_num = header & 0xFF;
        
        // Check for discard packets - skip but don't resync
        if (cam.is_discard_packet(cam.packet_buffer)) {
            discard_packets++;
            if (discard_packets > 20) {
                break;  // Too many discards, end of frame
            }
            continue;
        }
        
        // Skip segment 0 (appears between frames)
        if (segment == 0) {
            continue;
        }
        
        // Only accept valid segments (1-4) and packet numbers (0-59)
        if (segment >= 1 && segment <= 4 && packet_num <= 59) {
            valid_packets++;
            
            // Count by segment
            if (segment == 1) seg1_count++;
            else if (segment == 2) seg2_count++;
            else if (segment == 3) seg3_count++;
            else if (segment == 4) seg4_count++;
            
            // Print sample packets
            if (valid_packets % 20 == 0) {
                Serial.printf("Seg:%d Pkt:%d | Data: ", segment, packet_num);
                for (int j = 4; j < 10; j++) {
                    Serial.printf("%02X ", cam.packet_buffer[j]);
                }
                Serial.println();
            }
        } else {
            // Invalid packet - just skip it, don't resync immediately
            // Too many consecutive invalid packets will trigger resync below
        }
        
        // If we have enough valid packets, we got a frame
        if (valid_packets >= 200) {
            break;
        }
        
        if (i % 50 == 0) yield();
    }
    
    digitalWrite(SPI_CS, HIGH);
    
    // Print frame statistics
    frame_count++;
    Serial.printf("\n=== Frame %d ===\n", frame_count);
    Serial.printf("Valid packets: %d (S1:%d S2:%d S3:%d S4:%d)\n", 
                  valid_packets, seg1_count, seg2_count, seg3_count, seg4_count);
    Serial.printf("Discard: %d | Total read: %d\n\n", discard_packets, packets_read);
    
    // Only resync if we got very few valid packets
    if (valid_packets < 50) {
        resync_count++;
        Serial.printf("Low valid count - performing resync #%d\n", resync_count);
        cam.sync();
        delay(100);
    }
    
    delay(100);  // Brief pause between frames
}
