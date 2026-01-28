#include <Wire.h>
#include <SPI.h>

// ESP32 Pin Definitions
#define SPI_MOSI    23
#define SPI_MISO    19
#define SPI_SCK     18
#define SPI_CS      5
#define I2C_SDA     21
#define I2C_SCL     22
#define RESET_PIN   4  // Optional reset pin

byte x = 0;
#define ADDRESS  (0x2A)

void i2c_scanner() {
  byte error, address;
  int nDevices;
  Serial.println("Scanning I2C bus...");
  nDevices = 0;
  for(address = 1; address < 127; address++ ) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
    if (error == 0) {
      Serial.print("I2C device found at address 0x");
      if (address<16) Serial.print("0");
      Serial.println(address,HEX);
      nDevices++;
    }
    else if (error==4) {
      Serial.print("Unknown error at address 0x");
      if (address<16) Serial.print("0");
      Serial.println(address,HEX);
    }
  }
  if (nDevices == 0)
    Serial.println("No I2C devices found\n");
  else
    Serial.println("I2C scan complete\n");
}

#define AGC (0x01)
#define SYS (0x02)
#define VID (0x03)
#define OEM (0x08)

#define GET (0x00)
#define SET (0x01)
#define RUN (0x02)

#define VOSPI_FRAME_SIZE (164)

void setup()
{
  // Initialize Serial first
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n\nStarting Lepton IR Camera...");

  // Initialize Reset pin and reset the camera
  pinMode(RESET_PIN, OUTPUT);
  digitalWrite(RESET_PIN, LOW);   // Hold in reset
  delay(100);
  digitalWrite(RESET_PIN, HIGH);  // Release reset
  Serial.println("Camera reset complete");
  
  // Wait for camera boot (Lepton needs ~950ms)
  Serial.println("Waiting for camera boot...");
  delay(2000);
  
  // Initialize I2C with 100kHz clock (Lepton prefers slower speeds)
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(100000);  // 100 kHz I2C clock
  Serial.println("I2C initialized at 100kHz");
  
  // Scan I2C bus to verify camera presence
  i2c_scanner();
  
  // Initialize SPI CS pin
  pinMode(SPI_CS, OUTPUT);
  digitalWrite(SPI_CS, HIGH);
  
  // Initialize SPI with ESP32 pins
  SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI, SPI_CS);
  SPI.setDataMode(SPI_MODE3);
  SPI.setFrequency(20000000);  // 20 MHz SPI clock

  Serial.println("Setup complete\n");
}

int spi_read_word(int data)
{
  int read_data;
  // take the SS pin low to select the chip:
  digitalWrite(SPI_CS, LOW);
  //  send in the address and value via SPI:
  read_data = SPI.transfer(data >> 8) << 8;
  read_data |= SPI.transfer(data);
  // take the SS pin high to de-select the chip:
  digitalWrite(SPI_CS, HIGH);
  return read_data;
}

byte lepton_frame_packet[VOSPI_FRAME_SIZE];

#define IMAGE_SIZE (800)
byte image[IMAGE_SIZE];
int image_index;
void read_lepton_frame(void)
{
  int i;
  // Keep CS low for entire frame read
  digitalWrite(SPI_CS, LOW);
  delayMicroseconds(10);  // Small delay for camera to prepare
  
  for (i = 0; i < VOSPI_FRAME_SIZE; i++)
  {
    lepton_frame_packet[i] = SPI.transfer(0x00);
  }
  
  // Release CS after frame is complete
  digitalWrite(SPI_CS, HIGH);
  delayMicroseconds(185);  // Inter-frame delay
}

void lepton_sync(void)
{
  int i;
  int data = 0x0f;

  digitalWrite(SPI_CS, HIGH);
  delay(185);
  while ((data & 0x0f) == 0x0f)
  {
    digitalWrite(SPI_CS, LOW);
    data = SPI.transfer(0x00) << 8;
    data |= SPI.transfer(0x00);
    digitalWrite(SPI_CS, HIGH);

    for (i = 0; i < ((VOSPI_FRAME_SIZE - 2) / 2); i++)
    {
      digitalWrite(SPI_CS, LOW);
      SPI.transfer(0x00);
      SPI.transfer(0x00);
      digitalWrite(SPI_CS, HIGH);
    }
  }
}

void print_lepton_frame(void)
{
  int i;
  for (i = 0; i < (VOSPI_FRAME_SIZE); i++)
  {
    Serial.print(lepton_frame_packet[i], HEX);
    Serial.print(",");

  }
  Serial.println(" ");
}

void print_image(void)
{
  int i;
  for (i = 0; i < (IMAGE_SIZE); i++)
  {
    Serial.print(image[i], HEX);
    Serial.print(",");

  }
  Serial.println(" ");
}

void lepton_command(unsigned int moduleID, unsigned int commandID, unsigned int command)
{
  byte error;
  Wire.beginTransmission(ADDRESS);

  // Command Register is a 16-bit register located at Register Address 0x0004
  Wire.write(0x00);
  Wire.write(0x04);

  if (moduleID == 0x08) //OEM module ID
  {
    Wire.write(0x48);
  }
  else
  {
    Wire.write(moduleID & 0x0f);
  }
  Wire.write( ((commandID << 2 ) & 0xfc) | (command & 0x3));

  error = Wire.endTransmission();    // stop transmitting
  if (error != 0)
  {
    Serial.print("error=");
    Serial.println(error);
  }
}

void agc_enable()
{
  byte error;
  Wire.beginTransmission(ADDRESS); // transmit to device #4
  Wire.write(0x01);
  Wire.write(0x05);
  Wire.write(0x00);
  Wire.write(0x01);

  error = Wire.endTransmission();    // stop transmitting
  if (error != 0)
  {
    Serial.print("error=");
    Serial.println(error);
  }
}

void set_reg(unsigned int reg)
{
  byte error;
  Wire.beginTransmission(ADDRESS); // transmit to device #4
  Wire.write(reg >> 8 & 0xff);
  Wire.write(reg & 0xff);            // sends one byte

  error = Wire.endTransmission();    // stop transmitting
  if (error != 0)
  {
    Serial.print("error=");
    Serial.println(error);
  }
}

//Status reg 15:8 Error Code  7:3 Reserved 2:Boot Status 1:Boot Mode 0:busy

int read_reg(unsigned int reg)
{
  int reading = 0;
  set_reg(reg);

  Wire.requestFrom(ADDRESS, 2);

  reading = Wire.read();  // receive high byte (overwrites previous reading)
  //Serial.println(reading);
  reading = reading << 8;    // shift high byte to be high 8 bits

  reading |= Wire.read(); // receive low byte as lower 8 bits
  Serial.print("reg:");
  Serial.print(reg);
  Serial.print("==0x");
  Serial.print(reading, HEX);
  Serial.print(" binary:");
  Serial.println(reading, BIN);
  return reading;
}

int read_data()
{
  int i;
  int data;
  int payload_length;

  while (read_reg(0x2) & 0x01)
  {
    Serial.println("busy");
  }

  payload_length = read_reg(0x6);
  Serial.print("payload_length=");
  Serial.println(payload_length);

  Wire.requestFrom(ADDRESS, (uint8_t)payload_length);
  
  // Wait for data to arrive
  delay(10);
  
  // Only read the bytes that are actually available
  int available = Wire.available();
  for (i = 0; i < (available / 2); i++)
  {
    if (Wire.available() >= 2) {
      data = Wire.read() << 8;
      data |= Wire.read();
      Serial.println(data, HEX);
    }
  }
  Serial.println();  // Add blank line for readability
  
  return 0;  // Success
}


void loop()
{
  int i;
  int reading = 0;
  String debugString;
  Serial.println("beginTransmission");

  //set_reg(0);

  //read_reg(0x0);

  read_reg(0x2);


  Serial.println("SYS Camera Customer Serial Number");
  lepton_command(SYS, 0x28 >> 2 , GET);
  read_data();

  Serial.println("SYS Flir Serial Number");
  lepton_command(SYS, 0x2 , GET);
  read_data();

  Serial.println("SYS Camera Uptime");
  lepton_command(SYS, 0x0C >> 2 , GET);
  read_data();

  Serial.println("SYS Fpa Temperature Kelvin");
  lepton_command(SYS, 0x14 >> 2 , GET);
  read_data();

  Serial.println("SYS Aux Temperature Kelvin");
  lepton_command(SYS, 0x10 >> 2 , GET);
  read_data();

  Serial.println("OEM Chip Mask Revision");
  lepton_command(OEM, 0x14 >> 2 , GET);
  read_data();

  //Serial.println("OEM Part Number");
  //lepton_command(OEM, 0x1C >> 2 , GET);
  //read_data();

  Serial.println("OEM Camera Software Revision");
  lepton_command(OEM, 0x20 >> 2 , GET);
  read_data();

  Serial.println("AGC Enable");
  //lepton_command(AGC, 0x01  , SET);
  agc_enable();
  read_data();

  Serial.println("AGC READ");
  lepton_command(AGC, 0x00  , GET);
  read_data();

  // Serial.println("SYS Telemetry Enable State");
  //lepton_command(SYS, 0x19>>2 ,GET);
  // read_data();

  Serial.println("\n=== Starting continuous frame capture ===\n");
  
  // Read and display thermal frames continuously
  int frame_count = 0;
  while (1)
  {
    read_lepton_frame();
    
    // Print every 30th frame to avoid flooding serial
    if (frame_count % 30 == 0) {
      Serial.print("Frame ");
      Serial.print(frame_count);
      Serial.println(":");
      print_lepton_frame();
    }
    
    frame_count++;
    
    // CRITICAL: Yield to watchdog timer to prevent crash
    yield();
    delay(1);  // Small delay between frames
  }

  x++;
  delay(10000);
}