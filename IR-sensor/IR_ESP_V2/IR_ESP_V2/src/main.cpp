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
    SPI.setDataMode(SPI_MODE3); // Modus 3 fordi IDK

    var = cam.read_stat();
    Serial.print("Status: ");
    Serial.println(var);
    busy = cam.busy_bit();

    cam.sync();

}


void loop() {
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
    
    Serial.println("Kom ut av sync loop");
    cam.print_buffer(cam.packet_buffer);
    delay(1000);
}
