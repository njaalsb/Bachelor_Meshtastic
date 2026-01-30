/* Denne koden er ment for å teste FLIR lepton IR kameraet ved bruk av en ESP32. Det er tatt utgangspunkt i en eksempelkode
 * som det er linket til i readme. Eksempelkoden er skrevet i Arduino C, men dette er blitt endret til C++. 
 * I2C addressen til kameraet er: 0x2A
 */ 

 /* 
  * Kamera specs: Lepton 3/3.5
  * Image size: 160 x 120 = 19,200 pixels
  * RGB888 mode: 3 bytes per pixel = 57,600 bytes per frame
  * VoSPI Structure:
  *   - 4 segments per frame
  *   - 60 packets per segment
  *   - 240 total packets per frame
  *   - Each packet: 4 byte header + 160 byte payload = 164 bytes
  */

#include <Wire.h>
#include <SPI.h>

// ESP32 Pin deklarasjoner
#define SPI_MOSI    23
#define SPI_MISO    19
#define SPI_SCK     18
#define SPI_CS      5
#define I2C_SDA     21
#define I2C_SCL     22
#define RESET_PIN   4  // Optional reset pin

// Lepton 3 VoSPI Constants
#define VOSPI_PACKET_SIZE 164
#define PACKETS_PER_SEGMENT 60
#define SEGMENTS_PER_FRAME 4
#define PACKETS_PER_FRAME (PACKETS_PER_SEGMENT * SEGMENTS_PER_FRAME)  // 240
#define IMAGE_WIDTH 160
#define IMAGE_HEIGHT 120
#define RGB_BYTES_PER_PIXEL 3
#define IMAGE_BUFFER_SIZE (IMAGE_WIDTH * IMAGE_HEIGHT * RGB_BYTES_PER_PIXEL)  // 57,600 bytes

byte x = 0;
#define ADDRESS  (0x2A)

/*
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
*/

#define AGC (0x01)
#define SYS (0x02)
#define VID (0x03)
#define OEM (0x08)

#define GET (0x00)
#define SET (0x01)
#define RUN (0x02)

// Single packet buffer
byte packet_buffer[VOSPI_PACKET_SIZE];

// Full RGB888 image buffer (Warning: 57,600 bytes - might be tight on ESP32)
uint8_t rgb_image[IMAGE_BUFFER_SIZE];

void setup()
{
  Serial.begin(115200);
  delay(500);
  Serial.println("\n\nStarting Lepton IR Camera...");

  // Initialiserer Reset pin og reseter kameraet
  pinMode(RESET_PIN, OUTPUT);
  digitalWrite(RESET_PIN, LOW);   
  delay(100);
  digitalWrite(RESET_PIN, HIGH);  
  Serial.println("Camera reset complete");
  
  // Venter til kameraet booter (Lepton trenger ~950ms)
  Serial.println("Waiting for camera boot...");
  delay(2000);
  
  // Initialiserer I2C med 100kHz klokke (Lepton foretrekker angivelig litt lavere hastighet)
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(100000);  // 100 kHz I2C klokke
  Serial.println("I2C initialisert med frekvens på 100kHz");
  
  // Scan I2C bus to verify camera presence
  //i2c_scanner();
  
  // Initialiserer chipselect pinnen for SPI 
  pinMode(SPI_CS, OUTPUT);
  digitalWrite(SPI_CS, HIGH);
  
  // Initialiserer SPI med ESP32 pins
  SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI, SPI_CS);
  SPI.setDataMode(SPI_MODE3);
  SPI.setFrequency(20000000);  // 20 MHz SPI klokke

  Serial.println("Setup fullfort\n");
}

int spi_read_word(int data)
{
  int read_data;
  // Setter CS pinnen lav for å velge chip
  digitalWrite(SPI_CS, LOW);
  //  sender addresse og verdi via SPI
  read_data = SPI.transfer(data >> 8) << 8;
  read_data |= SPI.transfer(data);
  // Setter CS høy for å slutte å lese data:
  digitalWrite(SPI_CS, HIGH);
  return read_data;
}

// Lagrer frame pakken i typen byte 
byte lepton_frame_packet[VOSPI_PACKET_SIZE];

// Read a single VoSPI packet (164 bytes)
bool read_vospi_packet(byte* packet)
{
  digitalWrite(SPI_CS, LOW);
  delayMicroseconds(10);
  
  for (int i = 0; i < VOSPI_PACKET_SIZE; i++)
  {
    packet[i] = SPI.transfer(0x00);
  }
  
  digitalWrite(SPI_CS, HIGH);
  delayMicroseconds(10);
  
  // Check if this is a discard packet (ID bits all set)
  uint16_t packet_id = (packet[0] << 8) | packet[1];
  return (packet_id & 0x0F00) != 0x0F00;  // Returns false if discard packet
}

// Capture complete Lepton 3 frame (4 segments, 240 packets)
bool capture_lepton3_frame()
{
  int packets_received = 0;
  int segment = 0;
  int packet_in_segment = 0;
  int image_offset = 0;
  
  // Wait for segment 1 to start (segment 0 indicates start of frame)
  bool synced = false;
  int sync_attempts = 0;
  
  while (!synced && sync_attempts < 750)
  {
    if (read_vospi_packet(packet_buffer))
    {
      uint16_t packet_header = (packet_buffer[0] << 8) | packet_buffer[1];
      int packet_num = packet_header & 0x0FFF;
      int packet_segment = (packet_header >> 12) & 0x7;
      
      // Look for packet 0 or packet 20 in segment 1 (start of valid data)
      if (packet_segment == 1 && (packet_num == 0 || packet_num == 20))
      {
        synced = true;
        segment = 1;
        packet_in_segment = packet_num;
        
        // Copy this first packet's data (skip 4-byte header)
        for (int i = 0; i < 160; i++)
        {
          rgb_image[image_offset++] = packet_buffer[i + 4];
        }
        packets_received = 1;
      }
    }
    sync_attempts++;
    yield();
  }
  
  if (!synced)
  {
    Serial.println("Failed to sync with frame start");
    return false;
  }
  
  // Now read the rest of the frame
  while (packets_received < PACKETS_PER_FRAME && sync_attempts < 1000)
  {
    if (read_vospi_packet(packet_buffer))
    {
      uint16_t packet_header = (packet_buffer[0] << 8) | packet_buffer[1];
      int packet_num = packet_header & 0x0FFF;
      int packet_segment = (packet_header >> 12) & 0x7;
      
      // Verify sequential packet
      if (packet_segment >= 1 && packet_segment <= 4)
      {
        // Copy RGB data (skip 4-byte header)
        if (image_offset + 160 <= IMAGE_BUFFER_SIZE)
        {
          for (int i = 0; i < 160; i++)
          {
            rgb_image[image_offset++] = packet_buffer[i + 4];
          }
          packets_received++;
        }
      }
    }
    sync_attempts++;
    yield();
  }
  
  Serial.print("Captured ");
  Serial.print(packets_received);
  Serial.print(" packets, ");
  Serial.print(image_offset);
  Serial.println(" bytes");
  
  return (packets_received >= 200);  // Accept if we got most of the frame
}

// Sync funksjon
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
  for (i = 0; i < (VOSPI_PACKET_SIZE); i++)
  {
    Serial.print(lepton_frame_packet[i], HEX);
    Serial.print(",");
  }
  Serial.println(" ");
}

// Output RGB888 image in PPM format (can be saved and viewed)
void print_rgb_image_ppm()
{
  // PPM P6 format header
  Serial.println("P6");
  Serial.print(IMAGE_WIDTH);
  Serial.print(" ");
  Serial.println(IMAGE_HEIGHT);
  Serial.println("255");
  
  // Binary RGB data
  Serial.write(rgb_image, IMAGE_BUFFER_SIZE);
  Serial.println();
}

// Output RGB image as CSV (row,col,R,G,B) - useful for debugging
void print_rgb_image_csv()
{
  Serial.println("row,col,R,G,B");
  int pixel = 0;
  for (int row = 0; row < IMAGE_HEIGHT; row++)
  {
    for (int col = 0; col < IMAGE_WIDTH; col++)
    {
      int index = pixel * 3;
      Serial.print(row);
      Serial.print(",");
      Serial.print(col);
      Serial.print(",");
      Serial.print(rgb_image[index]);     // R
      Serial.print(",");
      Serial.print(rgb_image[index + 1]); // G
      Serial.print(",");
      Serial.println(rgb_image[index + 2]); // B
      pixel++;
    }
  }
}

// Output basic image statistics
void print_image_stats()
{
  uint32_t r_sum = 0, g_sum = 0, b_sum = 0;
  uint8_t r_min = 255, g_min = 255, b_min = 255;
  uint8_t r_max = 0, g_max = 0, b_max = 0;
  
  for (int i = 0; i < IMAGE_BUFFER_SIZE; i += 3)
  {
    uint8_t r = rgb_image[i];
    uint8_t g = rgb_image[i + 1];
    uint8_t b = rgb_image[i + 2];
    
    r_sum += r; g_sum += g; b_sum += b;
    if (r < r_min) r_min = r; if (r > r_max) r_max = r;
    if (g < g_min) g_min = g; if (g > g_max) g_max = g;
    if (b < b_min) b_min = b; if (b > b_max) b_max = b;
  }
  
  int total_pixels = IMAGE_WIDTH * IMAGE_HEIGHT;
  Serial.print("R: avg=");
  Serial.print(r_sum / total_pixels);
  Serial.print(" min=");
  Serial.print(r_min);
  Serial.print(" max=");
  Serial.println(r_max);
  
  Serial.print("G: avg=");
  Serial.print(g_sum / total_pixels);
  Serial.print(" min=");
  Serial.print(g_min);
  Serial.print(" max=");
  Serial.println(g_max);
  
  Serial.print("B: avg=");
  Serial.print(b_sum / total_pixels);
  Serial.print(" min=");
  Serial.print(b_min);
  Serial.print(" max=");
  Serial.println(b_max);
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
  Wire.beginTransmission(ADDRESS);
  Wire.write(0x01);
  Wire.write(0x05);
  Wire.write(0x00);
  Wire.write(0x01);

  error = Wire.endTransmission();
  if (error != 0)
  {
    Serial.print("AGC enable error=");
    Serial.println(error);
  }
}

// Enable RGB888 output format
void enable_rgb888_mode()
{
  Serial.println("Configuring RGB888 output mode...");
  
  // VID Output Format - Set to RGB888 (command ID 0x30, value 0x03 for RGB888)
  lepton_command(VID, 0x30 >> 2, SET);
  
  delay(100);
  
  // Write the RGB888 mode value (0x00000003)
  Wire.beginTransmission(ADDRESS);
  Wire.write(0x00);  // Data register high byte
  Wire.write(0xF8);  // Data register low byte (0x00F8)
  Wire.write(0x00);
  Wire.write(0x00);
  Wire.write(0x00);
  Wire.write(0x03);  // RGB888 mode = 3
  
  byte error = Wire.endTransmission();
  if (error != 0)
  {
    Serial.print("RGB888 config error=");
    Serial.println(error);
  }
  
  delay(500);  // Wait for camera to reconfigure
  Serial.println("RGB888 mode enabled");
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
  agc_enable();
  read_data();

  Serial.println("AGC READ");
  lepton_command(AGC, 0x00, GET);
  read_data();

  // Enable RGB888 output mode
  enable_rgb888_mode();

  Serial.println("\n=== Starting RGB888 frame capture (160x120) ===\n");
  Serial.println("Capturing thermal images in 24-bit RGB color...\n");
  
  int frame_count = 0;
  int successful_frames = 0;
  
  while (1)
  {
    // Capture complete RGB frame
    if (capture_lepton3_frame())
    {
      successful_frames++;
      
      // Every 10th successful frame, output statistics
      if (successful_frames % 10 == 0)
      {
        Serial.print("\n=== Frame ");
        Serial.print(successful_frames);
        Serial.println(" ===");
        print_image_stats();
        
        // Uncomment one of these to output full image:
        // print_rgb_image_ppm();  // PPM format - can save to .ppm file
        // print_rgb_image_csv();  // CSV format - easier to parse/debug
      }
    }
    else
    {
      Serial.println("Frame capture failed, resyncing...");
      delay(200);  // Wait before retrying
    }
    
    frame_count++;
    yield();
    delay(100);  // ~10 fps
  }

  x++;
  delay(10000);
}