#include <Arduino.h>
#include "IR.h"

int var;
// Instansierer kameraet
IR cam;
bool busy;

void setup() {
    Serial.begin(115200);

    // Configure 25MHz clock output on GPIO0
    cam.set_freq_out();

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
    

void loop(void) {
    while(1){
            
        static int frame_count = 0;
        static int resync_count = 0;
        
        // Start frame read: CS HIGH, wait for frame period, then CS LOW
        digitalWrite(SPI_CS, HIGH);
        delay(190);  // Wait >185ms for frame period (slightly longer for safety)
        digitalWrite(SPI_CS, LOW);
        delayMicroseconds(10);
        
        // Track packets in this frame read
        int packets_read = 0;
        int valid_packets = 0;
        int discard_packets = 0;
        int seg1_count = 0, seg2_count = 0, seg3_count = 0, seg4_count = 0;
        int invalid_packets = 0;
        
        bool segments_seen[5] = {false, false, false, false, false}; // Track segments 0-4
        
        // Read continuously for up to 400 packets (240 valid + overhead)
        for (int i = 0; i < 400; i++) {
            cam.read_vospi_packet(cam.packet_buffer);
            packets_read++;
            
            // Parse header
            int segment = cam.get_segment_number(cam.packet_buffer);
            int packet_num = cam.get_packet_number(cam.packet_buffer);
            
            // Check for discard packets
            if (cam.is_discard_packet(cam.packet_buffer)) {
                discard_packets++;
                // Multiple consecutive discards mean we're between frames/segments
                if (discard_packets > 15) {
                    break;  // End of frame boundary
                }
                continue;
            }
            
            // Skip segment 0 (telemetry/between frames)
            if (segment == 0) {
                continue;
            }
            
            // Only accept valid segments (1-4) and packet numbers (0-59)
            if (segment >= 1 && segment <= 4 && packet_num >= 0 && packet_num <= 59) {
                valid_packets++;
                segments_seen[segment] = true;
                
                // Count by segment
                if (segment == 1) seg1_count++;
                else if (segment == 2) seg2_count++;
                else if (segment == 3) seg3_count++;
                else if (segment == 4) seg4_count++;
                
                // Print sample packets for diagnostics
                if (valid_packets % 30 == 1) {
                    Serial.printf("Seg:%d Pkt:%d | Data: ", segment, packet_num);
                    for (int j = 4; j < 10; j++) {
                        Serial.printf("%02X ", cam.packet_buffer[j]);
                    }
                    Serial.println();
                }
            } else {
                // Track truly invalid packets (bad segment or packet number)
                invalid_packets++;
                if (invalid_packets > 20) {
                    Serial.printf("Too many invalid packets (Seg:%d Pkt:%d)\n", segment, packet_num);
                    break;
                }
            }
            
            // Check if we have a complete frame (all 4 segments with good coverage)
            if (valid_packets >= 200 && segments_seen[1] && segments_seen[2] && 
                segments_seen[3] && segments_seen[4]) {
                break;  // Good frame, exit early
            }
            
            if (i % 50 == 0) yield();
        }
        
        digitalWrite(SPI_CS, HIGH);
        
        // Print frame statistics
        frame_count++;
        Serial.printf("\n=== Frame %d ===\n", frame_count);
        Serial.printf("Valid: %d (S1:%d S2:%d S3:%d S4:%d) | Discard: %d | Invalid: %d | Total: %d\n", 
                    valid_packets, seg1_count, seg2_count, seg3_count, seg4_count,
                    discard_packets, invalid_packets, packets_read);
        
        // Resync logic: if we got very few valid packets or missing segments
        bool all_segments = segments_seen[1] && segments_seen[2] && segments_seen[3] && segments_seen[4];
        
        if (valid_packets < 100 || !all_segments) {
            resync_count++;
            Serial.printf("** SYNC LOST ** (Valid:%d, AllSegs:%d) - Resync #%d\n", 
                        valid_packets, all_segments, resync_count);
            cam.sync();
        } else {
            Serial.println("[Frame OK]");
        }
        
        delay(50);  // Brief pause between frames
    }
}
