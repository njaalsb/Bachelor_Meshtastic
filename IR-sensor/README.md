# FLIR Lepton 3.1R
- Infrarød bildesensor
- Kameraet styres over I2C
- Bildet overføres via SPI
- Oppløsning 160 x 120 pixler

### PINOUT-FLIR Lepton 3.1R

- Pin 1 - SCL: Camera Control Interface Clock, I2C
- Pin 2 - SDA: Camera Control Interface Data, I2C
- Pin 3 - VIN: 3-5 V Supply input
- Pin 4 - GND: Common Ground
- Pin 5 - CLK: Video Over SPI Slave Clock
- Pin 6 - MISO: Video Over SPI Slave Master In Slave Out
- Pin 7 - MOSI: Video Over SPI Slave Master Out Slave In
- Pin 8 - CS: Video Over SPI Slave Chip Select (active LOW)
- Pin 9 - VSYNC: VSync
- Pin 10 - EN: Enable, Active High

### Eksempelkode:
[Arduino C eksempelkode, utdatert](https://github.com/groupgets/LeptonModule/blob/master/software/arduino_i2c/Lepton.ino)

[Youtube video om IR-sensor](https://www.youtube.com/watch?v=NLrTN8MurZw)

### Firmware:
[Firmware ESP32T3S3](https://github.com/meshtastic/firmware/tree/develop/variants/esp32s3)

## PureThermal Breakout Board:

[Docs](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/694/250-0577-00_DS_1-2021.pdf)

### Pinout breakout board

![alt text](image.png)

![alt text](image-1.png)


## Oppkobling: 

NC = Not Connected/floating

- Pin1 - GND -> GND ESP
- Pin2 - 3.3V/5V -> 5V ESP
- PIN3 - VPROG -> NC
- PIN4 - VCC28 -> NC
- Pin5 - SDA -> PIN21 ESP
- PIN6 - VCC28_IO -> NC
- PIN7 - SPI_CLK -> PIN18 ESP
- PIN8 - SCL -> PIN22 ESP             
- PIN9 - SPI_MOSI -> PIN23 ESP
- PIN10 - SPI_CS -> PIN5 ESP
- PIN11 - GPIO0 -> NC
- PIN12 - SPI_MISO -> PIN19 ESP
- PIN13 - GPIO2 -> NC
- PIN14 - GPIO1 -> NC
- PIN15 - GPIO3/VSYNC -> NC 
- PIN16 - VCC12 -> NC
- Pin17 - Reset_L -> PIN4 ESP
- PIN18 - Master_CLK -> NC
- PIN19 - GND -> GND ESP
- PIN20 - PWN_DWN_L -> 3.3V

# Bildeformat:
Gjeldende konfigurasjon er følgende:
- 80 x 60 pixler
- 4 frames per bilde
- 60 packets per frame 
- 164 bytes per packet
- Discard packet format: Header 0x1FFF, binært: 0001 1111 1111 1111