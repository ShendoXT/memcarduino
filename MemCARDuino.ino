/*
  MemCARDuino - Arduino PlayStation 1 Memory Card reader
  Shendo 2013. - 2024.

  Compatible with:
  * Arduino Uno, Duemilanove, Diecimila, Nano, Mini, Fio (ATmega168/P or ATmega328/P).
  * Arduino Leonardo, Micro (ATmega32U4)
  * Arduino Mega 2560
  * Espressif ESP8266, ESP32
  * Raspberry Pi Pico

  Notes on the SPI communication:
    My tests have shown that most compatible form of comms is software based SPI bit bang method,
    especially with PocketStations which are notoriously difficult to communicate with.
    Downside is that it's the slowest form of data transfer, specially evident on old ATmegas.
    So, any platform that has enough processing power will use soft SPI for improved compatibility.
*/

#include "Arduino.h"
#include <SPI.h>

//Device Firmware identifier
#define IDENTIFIER "MCDINO"   //MemCARDuino
#define VERSION 0x09          //Firmware version byte (Major.Minor).

//Commands
#define GETID 0xA0            //Get identifier
#define GETVER 0xA1           //Get firmware version
#define MCREAD 0xA2           //Memory Card Read (frame)
#define MCWRITE 0xA3          //Memory Card Write (frame)

//PocketStation commands
#define PSINFO  0xB0          //PocketStation info dump
#define PSBIOS  0xB1          //PocketStation BIOS dump
#define PSTIME  0xB2          //Set PocketStation date and time

//Test commands
#define TEST 0x54             //ASCII 'T' - test command

//Responses
#define ERROR 0xE0            //Invalid command received (error)

//Memory Card Responses
#define RW_NO_CARD 0xFF       //No Memory Card connected
#define RW_GOOD 0x47          //Good
//0x4E - BadChecksum
//0xFF - BadSector

//Misc
#define MAX_RETRY_COUNT 5     //Number of retries before fallback

#ifndef ICACHE_RAM_ATTR
  #define ICACHE_RAM_ATTR
#endif

//Define pins for each known platform
#if defined (ESP8266)
  #define DataPin   12          //MISO aka Data
  #define CmndPin   13          //MOSI aka Command
  #define AttPin    15          //Attention (SS)
  #define ClockPin  14
  #define AckPin    2           //Acknowledge
#elif defined (ESP32)
  #define DataPin   19
  #define CmndPin   23
  #define AttPin    5
  #define ClockPin  18
  #define AckPin    22
#elif defined (ARDUINO_ARCH_RP2040)
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
bool SlowSPIMode = false;
byte ReadData[128];
int failedRWCount = 0;            //Count failed read/write attemps for fallback modes

//Set up pins for communication
void PinSetup()
{
  pinMode(AttPin, OUTPUT);
  pinMode(AckPin, INPUT_PULLUP);

  digitalWrite(AttPin, HIGH);

  //Set up SPI
#if defined (ARDUINO_ARCH_RP2040) || (ESP8266) || (ESP32)
  pinMode(ClockPin, OUTPUT);
  pinMode(CmndPin, OUTPUT);

  digitalWrite(ClockPin, HIGH);
  digitalWrite(CmndPin, HIGH);
#else
  SPI.begin();
  SPI.beginTransaction(SPISettings(125000, LSBFIRST, SPI_MODE3));
#endif

  //Enable pullup on MISO Data line
#if defined (__AVR_ATmega32U4__)
  /* Arduino Leonardo and Micro do not have exposed ICSP pins
   * so we have to enable pullup by referencing the port*/
  PORTB = (1<<PB3);
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
#ifdef ARDUINO_ARCH_RP2040
  pinMode(AckPin, INPUT_PULLUP);
#endif
}

//Acknowledge routine
ICACHE_RAM_ATTR void ACK()
{
  state = !state;
}

#if defined (ARDUINO_ARCH_RP2040) || (ESP8266) || (ESP32)
//Software SPI bit bang, turned out to be the most compatible with PocketStations
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
#if defined (ARDUINO_ARCH_RP2040) || (ESP8266) || (ESP32)
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

//Analyze status byte of the rw operations
void AnalyzeStatus(byte status){
  //Nothing to analyze, all good
  if(status == RW_GOOD) return;
}

//Read a frame from Memory Card and send it to serial port
void ReadFrame(unsigned int Address)
{
  byte AddressMSB = Address & 0xFF;
  byte AddressLSB = (Address >> 8) & 0xFF;
  byte StatusByte = 0;

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
  StatusByte = SendCommand(0x00, 500, 0);       //Memory Card status byte

  Serial.write(StatusByte);      //Memory Card status byte

  //Deactivate device
  digitalWrite(AttPin, HIGH);

  AnalyzeStatus(StatusByte);
}

//Write a frame from the serial port to the Memory Card
void WriteFrame(unsigned int Address)
{
  byte AddressMSB = Address & 0xFF;
  byte AddressLSB = (Address >> 8) & 0xFF;
  int DelayCounter = 30;

  //Use ACK detection mode by default
  CompatibleMode = false;

  //Copy 128 bytes from the serial input
  for (int i = 0; i < 128; i++)
  {
    while(!Serial.available())
    {
      DelayCounter--;
      if(DelayCounter == 0){
        return;    //If there is no response for 30ms stop writing (prevents lock on MemCARDuino)
      }delay(1);
    }

    ReadData[i] = Serial.read();
  }

  //Activate device
  digitalWrite(AttPin, LOW);
  delayMicroseconds(20);

  SendCommand(0x81, 300, 45);      //Access Memory Card
  SendCommand(0x57, 300, 45);      //Send write command
  SendCommand(0x00, 300, 45);      //Memory Card ID1
  SendCommand(0x00, 300, 45);      //Memory Card ID2
  SendCommand(AddressMSB, 300, 45);      //Address MSB
  SendCommand(AddressLSB, 300, 45);      //Address LSB

  //Write 128 byte data to the frame
  for (int i = 0; i < 128; i++)
  {
    SendCommand(ReadData[i], 150, 0);
  }

  SendCommand(Serial.read(), 200, 0);      //Checksum (MSB xor LSB xor Data)
  SendCommand(0x00, 200, 0);               //Memory Card ACK1
  SendCommand(0x00, 200, 0);               //Memory Card ACK2
  Serial.write(SendCommand(0x00, 0, 0));   //Memory Card status byte

  delayMicroseconds(500);

  //Deactivate device
  digitalWrite(AttPin, HIGH);
}

//Get info from PocketStation
void PSInfo(){

  //Activate device
  digitalWrite(AttPin, LOW);
  delayMicroseconds(20);

  SendCommand(0x81, 300, 45);               //Access Memory Card
  SendCommand(0x5A, 300, 45);               //Info command
  Serial.write(SendCommand(0x0, 300, 45));  //Data length

  for(int i=0; i < 0x12; i++){
    Serial.write(SendCommand(0x00, 300, 45));
  }

  //Deactivate device
  digitalWrite(AttPin, HIGH);
}

//Dump 16KB BIOS in parts
void PSBios(byte partNum){
  byte paramSize = 0;
  byte dataSize = 0;
  unsigned short address = partNum * 128;

  //Activate device
  digitalWrite(AttPin, LOW);
  delayMicroseconds(20);

  SendCommand(0x81, 300, 45);               //Access Memory Card
  SendCommand(0x5B, 300, 45);               //Download data
  SendCommand(0x01, 300, 45);               //Get Memory block function

  paramSize = SendCommand(0x00, 300, 45);   //Receive parameter size
  Serial.write(paramSize);

  //Unknown number of parameters returned, abort
  if(paramSize != 0x05){
    return;
  }

  SendCommand(address & 0xFF, 300, 45);     //Address 0-7
  SendCommand(address >> 8, 300, 45);       //Address 8-15
  SendCommand(0x00, 300, 45);               //Address 16-23
  SendCommand(0x04, 300, 45);               //Address 24-31

  SendCommand(0x80, 300, 45);               //Get 128 of data (max allowed)

  dataSize = SendCommand(0x00, 300, 45);   //Receive data size

  Serial.write(dataSize);

  //Unknown size returned, abort
  if(dataSize != 0x80){
    return;
  }

  for(int i = 0; i < 128; i++){
    Serial.write(SendCommand(0x80, 300, 45));
  }

  SendCommand(0x00, 300, 45);               //EOF

  //We will reply as RW good
  //As far as I know there is no XOR or anything to verify dumped data integrity
  Serial.write(RW_GOOD);

  //Deactivate device
  digitalWrite(AttPin, HIGH);
}

//Set PocketStation Data and Time
void PSTime(){
  byte paramSize = 0;
  byte dataSize = 0;
  int DelayCounter = 30;

  //Activate device
  digitalWrite(AttPin, LOW);
  delayMicroseconds(20);

  SendCommand(0x81, 300, 45);               //Access Memory Card
  SendCommand(0x5C, 300, 45);               //Upload data
  SendCommand(0x00, 300, 45);               //Set Date/Time

  paramSize = SendCommand(0x00, 300, 45);   //Receive parameter size
  Serial.write(paramSize);

  //Unknown number of parameters returned, abort
  if(paramSize != 0x00){
    return;
  }

  dataSize = SendCommand(0x00, 300, 45);   //Receive data size

  //Unknown length returned, abort
  if(dataSize != 0x08){
    return;
  }

  Serial.write(dataSize);

  //Copy 8 bytes from the serial input
  for (int i = 0; i < 8; i++)
  {
    while(!Serial.available())
    {
      DelayCounter--;
      if(DelayCounter == 0){
        digitalWrite(AttPin, HIGH);
        return;    //If there is no response for 30ms stop writing (prevents lock on MemCARDuino)
      }delay(1);
    }

    ReadData[i] = Serial.read();
  }

  //Send BCD data to PocketStation in the following order
  //Day, Month, Year, Century
  //Second, Minute, Hour, Day 
  for (int i = 0; i < 8; i++)
  {
    SendCommand(ReadData[i], 300, 45);
  }

  //End of transmission
  SendCommand(0x00, 300, 45);               //EOT

  //All good
  Serial.write(RW_GOOD);

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

      case TEST:
        Serial.print(IDENTIFIER);
        Serial.print(" ");
        Serial.print(VERSION >> 4);
        Serial.print(".");
        Serial.println(VERSION & 0xF, HEX);
        break;

      case PSINFO:
        PSInfo();
        break;

      case PSBIOS:
        delay(5);
        PSBios(Serial.read());
        break;

      case PSTIME:
        PSTime();
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
