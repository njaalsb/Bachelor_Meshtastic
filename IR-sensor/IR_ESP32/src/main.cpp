/* Denne koden er ment for å teste FLIR lepton IR kameraet ved bruk av en ESP32. Det er tatt utgangspunkt i en eksempelkode
 * som det er linket til i readme. Eksempelkoden er skrevet i Arduino C, men dette er blitt endret til C++. 
 * I2C addressen til kameraet er: 0x2A
 */ 

 /* 
  * Kamera specs: Lepton 3.1R (3/3.5)
  * Image size: 160 x 120 = 19,200 pixels
  * Raw14 mode (default): 2 bytes per pixel (14-bit thermal values)
  * VoSPI Structure:
  *   - 4 segments per frame
  *   - 60 packets per segment
  *   - 240 total packets per frame
  *   - Each packet: 4 byte header + 160 byte payload = 164 bytes
  *   - Payload: 80 pixels per packet (2 bytes each, 16-bit with upper 2 bits reserved)
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
#define PIXELS_PER_PACKET 80  // 160 bytes / 2 bytes per pixel
#define IMAGE_BUFFER_SIZE (IMAGE_WIDTH * IMAGE_HEIGHT * 2)  // 38,400 bytes (16-bit thermal values)

byte x = 0;
#define ADDRESS (0x2A)
#define AGC (0x01)
#define SYS (0x02)
#define VID (0x03)
#define OEM (0x08)

#define GET (0x00)
#define SET (0x01)
#define RUN (0x02)

// Single packet buffer
byte packet_buffer[VOSPI_PACKET_SIZE];

// Full thermal image buffer (16-bit values)
uint16_t thermal_image[IMAGE_WIDTH * IMAGE_HEIGHT];  // 19,200 pixels

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
  SPI.setFrequency(10000000);  // 10 MHz SPI klokke (lower for stability)

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
// CS must already be LOW when calling this function
void read_vospi_packet(byte* packet)
{
  for (int i = 0; i < VOSPI_PACKET_SIZE; i++)
  {
    packet[i] = SPI.transfer(0x00);
  }
}

// Check if packet is a discard packet
bool is_discard_packet(byte* packet)
{
  uint16_t packet_id = (packet[0] << 8) | packet[1];
  return (packet_id & 0x0F00) == 0x0F00;
}

// Get packet number from header
int get_packet_number(byte* packet)
{
  uint16_t packet_header = (packet[0] << 8) | packet[1];
  return packet_header & 0x0FFF;
}

// Get segment number from header
int get_segment_number(byte* packet)
{
  uint16_t packet_header = (packet[0] << 8) | packet[1];
  return (packet_header >> 12) & 0x7;
}

// Debug: Print first N packets to see what we're receiving
void debug_print_packets(int count)
{
  Serial.println("\n=== DEBUG: Reading first packets from camera ===");
  digitalWrite(SPI_CS, HIGH);
  delay(185);
  digitalWrite(SPI_CS, LOW);
  delayMicroseconds(10);
  
  int discard_count = 0;
  int valid_count = 0;
  
  for (int i = 0; i < count; i++)
  {
    read_vospi_packet(packet_buffer);
    
    uint16_t header = (packet_buffer[0] << 8) | packet_buffer[1];
    int pkt_num = get_packet_number(packet_buffer);
    int pkt_seg = get_segment_number(packet_buffer);
    bool is_discard = is_discard_packet(packet_buffer);
    
    if (is_discard) {
      discard_count++;
      if (i < 20 || (i % 50 == 0)) {  // Print first 20 and every 50th
        Serial.print("Pkt ");
        Serial.print(i);
        Serial.println(": DISCARD");
      }
    } else {
      valid_count++;
      Serial.print("Pkt ");
      Serial.print(i);
      Serial.print(": Header=0x");
      Serial.print(header, HEX);
      Serial.print(" Seg=");
      Serial.print(pkt_seg);
      Serial.print(" Num=");
      Serial.print(pkt_num);
      Serial.print(" Data[4-7]=");
      for (int j = 4; j < 8; j++)
      {
        if (packet_buffer[j] < 0x10) Serial.print("0");
        Serial.print(packet_buffer[j], HEX);
        Serial.print(" ");
      }
      Serial.println();
    }
    
    if (i % 20 == 0) yield();
  }
  
  digitalWrite(SPI_CS, HIGH);
  Serial.print("Summary: ");
  Serial.print(valid_count);
  Serial.print(" valid, ");
  Serial.print(discard_count);
  Serial.println(" discard");
  Serial.println("=== DEBUG complete ===\n");
}

// Capture complete Lepton 3 frame (raw thermal data)
bool capture_lepton3_frame()
{
  int valid_packets = 0;
  int packets_read = 0;
  int max_packets = 800;  // Read enough to capture full frame plus some overhead
  
  int packets_per_segment[5] = {0, 0, 0, 0, 0};
  
  // Clear the thermal image buffer
  memset(thermal_image, 0, sizeof(thermal_image));
  
  // Wait between frames, then start continuous read
  digitalWrite(SPI_CS, HIGH);
  delay(185);
  digitalWrite(SPI_CS, LOW);
  delayMicroseconds(10);
  
  // Continuously read packets and store any valid ones
  while (packets_read < max_packets && valid_packets < PACKETS_PER_FRAME)
  {
    read_vospi_packet(packet_buffer);
    packets_read++;
    
    // Skip discard packets
    if (is_discard_packet(packet_buffer))
    {
      continue;
    }
    
    // Parse packet header
    int pkt_num = get_packet_number(packet_buffer);
    int pkt_seg = get_segment_number(packet_buffer);
    
    // Skip segment 0 (resyncing)
    if (pkt_seg == 0)
      continue;
    
    // Only process valid packets from segments 1-4 with packet numbers 0-59
    if (pkt_seg >= 1 && pkt_seg <= 4 && pkt_num >= 0 && pkt_num < PACKETS_PER_SEGMENT)
    {
      packets_per_segment[pkt_seg]++;
      
      // Calculate pixel position for this packet
      int segment_row_offset = (pkt_seg - 1) * PACKETS_PER_SEGMENT;
      int packet_row = segment_row_offset + pkt_num;
      
      // For Lepton 3: packets are sent in pairs (2 packets per image row)
      int image_row = packet_row / 2;
      int packet_in_row = packet_row % 2;
      
      // Calculate starting pixel index in the thermal_image buffer
      int pixel_start = (image_row * IMAGE_WIDTH) + (packet_in_row * PIXELS_PER_PACKET);
      
      // Extract 80 thermal pixels from the packet payload (skip 4-byte header)
      if (pixel_start >= 0 && pixel_start + PIXELS_PER_PACKET <= IMAGE_WIDTH * IMAGE_HEIGHT)
      {
        for (int i = 0; i < PIXELS_PER_PACKET; i++)
        {
          int payload_offset = 4 + (i * 2);
          uint16_t thermal_value = (packet_buffer[payload_offset] << 8) | packet_buffer[payload_offset + 1];
          
          // Only write if not already written (avoid overwriting with duplicate packets)
          if (thermal_image[pixel_start + i] == 0)
          {
            thermal_image[pixel_start + i] = thermal_value;
          }
        }
        valid_packets++;
      }
    }
    
    if (packets_read % 100 == 0)
      yield();
  }
  
  digitalWrite(SPI_CS, HIGH);
  
  Serial.print("Captured ");
  Serial.print(valid_packets);
  Serial.print("/");
  Serial.print(PACKETS_PER_FRAME);
  Serial.print(" packets (");
  for (int i = 1; i <= 4; i++)
  {
    Serial.print("S");
    Serial.print(i);
    Serial.print(":");
    Serial.print(packets_per_segment[i]);
    if (i < 4) Serial.print(" ");
  }
  Serial.print("), ");
  Serial.print(packets_read);
  Serial.println(" total read");
  
  return (valid_packets >= 180);  // Accept if we got at least 75% of packets
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

    for (i = 0; i < ((VOSPI_PACKET_SIZE - 2) / 2); i++)
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

// Output thermal image statistics
void print_thermal_stats()
{
  uint32_t sum = 0;
  uint16_t min_val = 65535;
  uint16_t max_val = 0;
  int zero_count = 0;
  
  for (int i = 0; i < IMAGE_WIDTH * IMAGE_HEIGHT; i++)
  {
    uint16_t val = thermal_image[i];
    sum += val;
    if (val < min_val) min_val = val;
    if (val > max_val) max_val = val;
    if (val == 0) zero_count++;
  }
  
  int total_pixels = IMAGE_WIDTH * IMAGE_HEIGHT;
  Serial.print("Thermal: avg=");
  Serial.print(sum / total_pixels);
  Serial.print(" min=");
  Serial.print(min_val);
  Serial.print(" max=");
  Serial.print(max_val);
  Serial.print(" zeros=");
  Serial.println(zero_count);
}

// Output sample thermal values (center and corners)
void print_thermal_samples()
{
  Serial.println("Sample thermal values:");
  Serial.print("  Top-left (0,0): ");
  Serial.println(thermal_image[0]);
  
  Serial.print("  Top-right (0,159): ");
  Serial.println(thermal_image[159]);
  
  Serial.print("  Center (60,80): ");
  Serial.println(thermal_image[60 * IMAGE_WIDTH + 80]);
  
  Serial.print("  Bottom-left (119,0): ");
  Serial.println(thermal_image[119 * IMAGE_WIDTH]);
  
  Serial.print("  Bottom-right (119,159): ");
  Serial.println(thermal_image[119 * IMAGE_WIDTH + 159]);
}

// Output thermal image as CSV for analysis
void print_thermal_csv()
{
  Serial.println("row,col,thermal_value");
  for (int row = 0; row < IMAGE_HEIGHT; row++)
  {
    for (int col = 0; col < IMAGE_WIDTH; col++)
    {
      int index = row * IMAGE_WIDTH + col;
      Serial.print(row);
      Serial.print(",");
      Serial.print(col);
      Serial.print(",");
      Serial.println(thermal_image[index]);
    }
    if (row % 10 == 0)
      yield();  // Allow ESP32 to handle background tasks
  }
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
  
  delay(100);
  Serial.println("AGC enabled");
}

// Disable telemetry (Lepton 3 specific - telemetry interferes with frame capture)
void disable_telemetry()
{
  Serial.println("Disabling telemetry...");
  
  // SYS Telemetry Enable State - Set to disabled (0x0218, SET)
  lepton_command(SYS, 0x18 >> 2, SET);
  delay(50);
  
  // Write disabled value (0x00000000)
  Wire.beginTransmission(ADDRESS);
  Wire.write(0x00);  // Data register address high
  Wire.write(0xF8);  // Data register address low (0x00F8)
  Wire.write(0x00);
  Wire.write(0x00);
  Wire.write(0x00);
  Wire.write(0x00);  // Telemetry disabled = 0
  
  byte error = Wire.endTransmission();
  if (error != 0)
  {
    Serial.print("Telemetry disable error=");
    Serial.println(error);
  }
  
  delay(200);
  Serial.println("Telemetry disabled");
}

// Perform VoSPI resync by deasserting then reasserting CS
void vospi_resync()
{
  Serial.println("Performing VoSPI resync...");
  digitalWrite(SPI_CS, HIGH);
  delay(185);  // Wait >185ms for frame period
  digitalWrite(SPI_CS, LOW);
  delayMicroseconds(10);
  
  // Read and discard packets until we get out of segment 0
  int attempts = 0;
  while (attempts < 300)
  {
    read_vospi_packet(packet_buffer);
    int seg = get_segment_number(packet_buffer);
    
    if (seg >= 1 && seg <= 4)
    {
      Serial.print("VoSPI synced! Found segment ");
      Serial.println(seg);
      digitalWrite(SPI_CS, HIGH);
      return;
    }
    attempts++;
  }
  
  digitalWrite(SPI_CS, HIGH);
  Serial.println("VoSPI resync timeout");
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

  Serial.println("OEM Camera Software Revision");
  lepton_command(OEM, 0x20 >> 2 , GET);
  read_data();

  Serial.println("AGC Enable");
  agc_enable();

  Serial.println("AGC READ");
  lepton_command(AGC, 0x00, GET);
  read_data();

  // Disable telemetry - critical for proper frame capture on Lepton 3
  disable_telemetry();
  
  // Perform initial VoSPI resync
  vospi_resync();

  // Debug: See what packets we're actually receiving after resync
  Serial.println("\nRunning packet debug after telemetry disable...");
  debug_print_packets(100);

  Serial.println("\n=== Starting thermal frame capture (160x120, Raw14) ===\n");
  Serial.println("Lepton 3.1R outputs 14-bit raw thermal values\n");
  
  int frame_count = 0;
  int successful_frames = 0;
  
  while (1)
  {
    // Capture complete thermal frame
    if (capture_lepton3_frame())
    {
      successful_frames++;
      
      // Every 10th successful frame, output statistics
      if (successful_frames % 10 == 0)
      {
        Serial.print("\n=== Frame ");
        Serial.print(successful_frames);
        Serial.println(" ===");
        print_thermal_stats();
        print_thermal_samples();
        
        // Uncomment to output full thermal CSV (warning: large output!)
        // print_thermal_csv();
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