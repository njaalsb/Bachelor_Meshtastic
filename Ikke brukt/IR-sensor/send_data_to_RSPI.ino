#include <HardwareSerial.h>

#define RXD2 16      // GPIO16 as RX
#define TXD2 17      // GPIO17 as TX
#define BAUD 115200  // baud rate

HardwareSerial mySerial(2); // Use Serial2

void setup() {
  Serial.begin(BAUD);
  mySerial.begin(BAUD, SERIAL_8N1, RXD2, TXD2);
}

void loop()
{
    uint16_t data = 0; //insert data input
    mySerial.println(String(data));
    delay(1);
}
