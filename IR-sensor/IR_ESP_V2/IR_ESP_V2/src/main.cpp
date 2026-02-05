#include <Arduino.h>
#include "IR.h"

// Instansierer kameraet
IR cam;

void setup() {
  pinMode(RESET_PIN, OUTPUT);
  Serial.begin(115200);
  cam.I2C_connect();
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
