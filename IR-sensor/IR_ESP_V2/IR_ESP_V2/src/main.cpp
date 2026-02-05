#include <Arduino.h>
#include "IR.h"

// Instansierer kameraet
IR cam;

void setup() {
  Serial.begin(115200);

  pinMode(RESET_PIN, OUTPUT);
  pinMode(SPI_CS, OUTPUT);
  
  cam.I2C_connect();

  SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI, SPI_CS);
  SPI.setDataMode(SPI_MODE3); // Modus 3 fordi IDK
}

void loop() {
  delay(2000);
  int var;
  //Serial.print("Kamerastatus:");

  var = cam.read_stat();
  Serial.print("Status: ");
  Serial.println(var);

  Serial.print("Powerstatus:");
  Serial.println(cam.read_power());
}
