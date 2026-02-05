#include <Arduino.h>
#include "IR.h"

// Instansierer kameraet
IR cam;

void setup() {
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


  if(var != 0){
    while(true){
      Serial.println(var);
      delay(100);
    }
  }
  //Serial.print("Powerstatus:");
  //Serial.println(cam.read_power());
}
