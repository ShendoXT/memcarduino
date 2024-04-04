/*
  MemCARDuino - Arduino PlayStation 1 Memory Card reader
  Shendo 2013. - 2024.

  Compatible with:
  * Arduino Uno, Duemilanove, Diecimila, Nano, Mini, Fio (ATmega168/P or ATmega328/P).
  * Arduino Leonardo, Micro (ATmega32U4)
  * Arduino Mega 2560
  * Espressif ESP8266, ESP32
  * Raspberry Pi Pico
*/

#include "Arduino.h"
#include <SPI.h>

//Device Firmware identifier
#define IDENTIFIER "MCDINO"   //MemCARDuino
#define VERSION 0x07          //Firmware version byte (Major.Minor).

//Commands
#define GETID 0xA0            //Get identifier
#define GETVER 0xA1           //Get firmware version
#define MCREAD 0xA2           //Memory Card Read (frame)
#define MCWRITE 0xA3          //Memory Card Write (frame)

//Responses
#define ERROR 0xE0            //Invalid command received (error)

//Memory Card Responses
//0x47 - Good
//0x4E - BadChecksum
//0xFF - BadSector

#ifndef ICACHE_RAM_ATTR
  #define ICACHE_RAM_ATTR
#endif

//Define pins for each known platform
#ifdef ESP8266
  #define DataPin   12          //MISO aka Data
  #define AttPin    15          //Attention (SS)
  #define AckPin    2           //Acknowledge
#elif defined (ESP32)
  #define DataPin   19
  #define CmndPin   23
  #define AttPin    5
  #define ClockPin  18
  #define AckPin    22
#elif defined (ARDUINO_ARCH_MBED_RP2040)
  #define DataPin   16
  #define CmndPin   19
  #define AttPin    17
  #define ClockPin  18
  #define AckPin    20
#elif defined (ARDUINO_AVR_MEGA2560)
  #define DataPin   50
  #define AttPin    53
  #define AckPin    2
#else
  #define DataPin   12
  #define AttPin    10
  #define AckPin    2
#endif

volatile int state = HIGH;
bool CompatibleMode = false;
byte ReadData[128];

//Set up pins for communication
void PinSetup()
{
  pinMode(AttPin, OUTPUT);
  pinMode(AckPin, INPUT_PULLUP);

  digitalWrite(AttPin, HIGH);

#ifdef ARDUINO_ARCH_MBED_RP2040
  pinMode(ClockPin, OUTPUT);
  pinMode(CmndPin, OUTPUT);

  digitalWrite(ClockPin, HIGH);
  digitalWrite(CmndPin, HIGH);
#else

#if ESP32
  SPI.begin(ClockPin, DataPin, CmndPin, -1);
#else
  SPI.begin();
#endif
  /* Memory Cards on PS1 are accessed at 250Khz but for the compatibility sake
   * we will use 125Khz. For higher speeds external pull-ups are recommended.*/
  SPI.beginTransaction(SPISettings(125000, LSBFIRST, SPI_MODE3));
#endif

  //Enable pullup on MISO Data line
#if defined(__AVR_ATmega32U4__)
  /* Arduino Leonardo and Micro do not have exposed ICSP pins
   * so we have to enable pullup by referencing the port*/
  PORTB = (1<<PB3);
#elif defined(ESP8266)
  /* ESP8266 needs to have each pin reconfigured for a specific purpose.
   * If we just write pin as INPUT_PULLUP it will lose it's function as MISO line
   * Therefore we need to adjust it as MISO with pullup...*/
  PIN_PULLUP_EN(PERIPHS_IO_MUX_MTDI_U);
#else
  pinMode(DataPin, INPUT_PULLUP);
#endif

  /* Set up interrupt for ACK signal from the Memory Card.
   *
   * Should be FALLING because signal goes LOW for ~5uS during ACK 
   * but ESP8266 for some reason doesn't register it.
   * So since it goes HIGH anyway after that we will use RISING */
  attachInterrupt(digitalPinToInterrupt(AckPin), ACK, RISING);

  //Pico needs to be reminded of the ack pin configuration...
#ifdef ARDUINO_ARCH_MBED_RP2040
  pinMode(AckPin, INPUT_PULLUP);
#endif
}

//Acknowledge routine
ICACHE_RAM_ATTR void ACK()
{
  state = !state;
}

//Software SPI bit bang, for devices without SPI or with SPI issues
#ifdef ARDUINO_ARCH_MBED_RP2040
byte SoftTransfer(byte data)
{
  byte outData = 0;

  for (int i = 0; i < 8; i++)  {
        digitalWrite(CmndPin, !!(data & (1 << i)));

        //Clock
        digitalWrite(ClockPin, LOW);
        delayMicroseconds(2);

        //Sample input data
        outData |= digitalRead(DataPin) << i;
        digitalWrite(ClockPin, HIGH);
        delayMicroseconds(2);
  }

  return outData;
}
#endif

//Send a command to PlayStation port using SPI
byte SendCommand(byte CommandByte, int Timeout, int Delay)
{
    if(!CompatibleMode) Timeout = 3000;
    state = HIGH; //Set high state for ACK signal

    //Delay for a bit (values simulating delays between real PS1 and Memory Card)
    delayMicroseconds(Delay);

    //Send data on the SPI bus
#ifdef ARDUINO_ARCH_MBED_RP2040
  /* Raspberry Pi Pico currently has some issues with SPI data corruption.
   * So for now we are gonna do some bit banging, Pico has plenty of power to do it in software.*/
    byte data = SoftTransfer(CommandByte);
#else
    byte data = SPI.transfer(CommandByte);
#endif

    //Wait for the ACK signal from the Memory Card
    while(state == HIGH)
    {
      Timeout--;
      delayMicroseconds(1);
      if(Timeout == 0){
        //Timeout reached, card doesn't report ACK properly
        CompatibleMode = true;
        break;
      }
    }

  return data;                    //Return the received byte
}

//Read a frame from Memory Card and send it to serial port
void ReadFrame(unsigned int Address)
{
  byte AddressMSB = Address & 0xFF;
  byte AddressLSB = (Address >> 8) & 0xFF;

  //Use ACK detection mode by default
  CompatibleMode = false;

  //Activate device
  digitalWrite(AttPin, LOW);
  delayMicroseconds(20);

  SendCommand(0x81, 500, 70);      //Access Memory Card
  SendCommand(0x52, 500, 45);      //Send read command
  SendCommand(0x00, 500, 45);      //Memory Card ID1
  SendCommand(0x00, 500, 45);      //Memory Card ID2
  SendCommand(AddressMSB, 500, 45);      //Address MSB
  SendCommand(AddressLSB, 500, 45);      //Address LSB
  SendCommand(0x00, 2800, 45);      //Memory Card ACK1
  SendCommand(0x00, 2800, 0);      //Memory Card ACK2
  SendCommand(0x00, 2800, 0);      //Confirm MSB
  SendCommand(0x00, 2800, 0);      //Confirm LSB

  //Get 128 byte data from the frame
  for (int i = 0; i < 128; i++)
  {
    Serial.write(SendCommand(0x00, 150, 0));
  }

  Serial.write(SendCommand(0x00, 500, 0));      //Checksum (MSB xor LSB xor Data)
  Serial.write(SendCommand(0x00, 500, 0));      //Memory Card status byte

  //Deactivate device
  digitalWrite(AttPin, HIGH);
}

//Write a frame from the serial port to the Memory Card
void WriteFrame(unsigned int Address)
{
  byte AddressMSB = Address & 0xFF;
  byte AddressLSB = (Address >> 8) & 0xFF;
  int DelayCounter = 30;

  //Use ACK detection mode by default
  CompatibleMode = false;

  //Activate device
  digitalWrite(AttPin, LOW);
  delayMicroseconds(20);

  SendCommand(0x81, 300, 45);      //Access Memory Card
  SendCommand(0x57, 300, 45);      //Send write command
  SendCommand(0x00, 300, 45);      //Memory Card ID1
  SendCommand(0x00, 300, 45);      //Memory Card ID2
  SendCommand(AddressMSB, 300, 45);      //Address MSB
  SendCommand(AddressLSB, 300, 45);      //Address LSB

  //Copy 128 bytes from the serial input
  for (int i = 0; i < 128; i++)
  {
    while(!Serial.available())
    {
      DelayCounter--;
      if(DelayCounter == 0)return;    //If there is no response for 30ms stop writing (prevents lock on MemCARDuino)
      delay(1);
    }

    ReadData[i] = Serial.read();
  }

  //Write 128 byte data to the frame
  for (int i = 0; i < 128; i++)
  {
    SendCommand(ReadData[i], 150, 0);
  }

  SendCommand(Serial.read(), 200, 0);      //Checksum (MSB xor LSB xor Data)
  SendCommand(0x00, 200, 0);               //Memory Card ACK1
  SendCommand(0x00, 200, 0);               //Memory Card ACK2
  Serial.write(SendCommand(0x00, 0, 0)); //Memory Card status byte

  //Deactivate device
  digitalWrite(AttPin, HIGH);
}

void setup()
{
  //Set up serial communication
  Serial.begin(115200);

  //Set up pins
  PinSetup();
}

void loop()
{
  //Listen for commands
  if(Serial.available() > 0)
  {
    switch(Serial.read())
    {
      default:
        Serial.write(ERROR);
        break;

      case GETID:
        Serial.write(IDENTIFIER);
        break;

      case GETVER:
        Serial.write(VERSION);
        break;

      case MCREAD:
        delay(5);
        ReadFrame(Serial.read() | Serial.read() << 8);
        break;

      case MCWRITE:
        delay(5);
        WriteFrame(Serial.read() | Serial.read() << 8);
        break;
    }
  }
}
