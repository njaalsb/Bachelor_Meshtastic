#include <Arduino.h>
#include "IR.h"


void setup() {
  Serial.begin(115200);
  I2C_connect();
}

void loop() {
  Serial.println("...");
  delay(1000);
}
