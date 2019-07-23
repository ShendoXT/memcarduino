/*
  MemCARDuino - Arduino PlayStation 1 Memory Card reader
  Shendo 2013. - 2016.

  Compatible with Arduino/Genuino Uno, Duemilanove, Diecimila, Nano, Mini,
  basically any board with ATmega168/P or ATmega328/P.

  Also compatible with Arduino Mega 2560 (and probably other ATMega2560 based boards)
*/

#include <Arduino.h>
#include <SPI.h>

//Device Firmware identifier
#define IDENTIFIER "MCDINO"  //MemCARDuino
#define VERSION 0x04         //Firmware version byte (Major.Minor)

//Commands
#define GETID 0xA0          //Get identifier
#define GETVER 0xA1         //Get firmware version
#define MCREAD 0xA2         //Memory Card Read (frame)
#define MCWRITE 0xA3        //Memory Card Write (frame)

//Responses
#define ERROR 0xE0         //Invalid command received (error)

//Memory Card Responses
//0x47 - Good
//0x4E - BadChecksum
//0xFF - BadSector

//Define pins
// If you are changing this for another board, note that:
// DataPin must be the MISO SPI pin
// CmdPin must be the MOSI SPI pin
// AttPin should be the SS SPI pin (but if you change it make sure to set the real SS SPI is set to output, otherwise you may run into trouble)
// ClockPin must be the SCK SPI pin
// AckPin must be the pin attached to INT0
#ifdef ARDUINO_AVR_MEGA2560
#define DataPin 50         //Data
#define CmdPin 51          //Command
#define AttPin 53          //Attention (Select)
#define ClockPin 52        //Clock
#define AckPin 2           //Acknowledge
#else
#define DataPin 12         //Data
#define CmdPin 11          //Command
#define AttPin 10          //Attention (Select)
#define ClockPin 13        //Clock
#define AckPin 2           //Acknowledge
#endif

byte ReadByte = 0;
volatile int state = HIGH;
bool CompatibleMode = false;

//Set up pins for communication
void PinSetup()
{
  byte clr = 0;

  pinMode(DataPin, INPUT);
  pinMode(CmdPin, OUTPUT);
  pinMode(AttPin, OUTPUT);
  pinMode(ClockPin, OUTPUT);
  pinMode(AckPin, INPUT);

  digitalWrite(DataPin, HIGH);    //Activate pullup resistor
  digitalWrite(CmdPin, LOW);
  digitalWrite(AttPin, HIGH);
  digitalWrite(ClockPin, HIGH);
  digitalWrite(AckPin, HIGH);    //Activate pullup resistor

  //Set up interrupt on pin 2 (INT.0) for Acknowledge signal
  attachInterrupt(0, ACK, FALLING);
}

//Acknowledge routine
void ACK()
{
  state = !state;
}

//Send a command to PlayStation port using SPI
byte SendCommand(byte CommandByte, int Delay)
{
    if(!CompatibleMode) Delay = 3000;   //Timeout
    state = HIGH;                       //Set high state for ACK signal

    uint8_t data = SPI.transfer(CommandByte);

    //Wait for the ACK signal from the Memory Card
    while(state == HIGH)
    {
      Delay--;
      delayMicroseconds(1);
      if(Delay == 0){
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
  SPI.beginTransaction(SPISettings(250000, LSBFIRST, SPI_MODE3));

  SendCommand(0x81, 500);      //Access Memory Card
  SendCommand(0x52, 500);      //Send read command
  SendCommand(0x00, 500);      //Memory Card ID1
  SendCommand(0x00, 500);      //Memory Card ID2
  SendCommand(AddressMSB, 500);      //Address MSB
  SendCommand(AddressLSB, 500);      //Address LSB
  SendCommand(0x00, 2800);      //Memory Card ACK1
  SendCommand(0x00, 2800);      //Memory Card ACK2
  SendCommand(0x00, 2800);      //Confirm MSB
  SendCommand(0x00, 2800);      //Confirm LSB

  //Get 128 byte data from the frame
  for (int i = 0; i < 128; i++)
  {
    Serial.write(SendCommand(0x00, 150));
  }

  Serial.write(SendCommand(0x00, 500));      //Checksum (MSB xor LSB xor Data)
  Serial.write(SendCommand(0x00, 500));      //Memory Card status byte

  //Deactivate device
  digitalWrite(AttPin, HIGH);
  SPI.endTransaction();
}

//Write a frame from the serial port to the Memory Card
void WriteFrame(unsigned int Address)
{
  byte AddressMSB = Address & 0xFF;
  byte AddressLSB = (Address >> 8) & 0xFF;
  byte ReadData[128];
  int DelayCounter = 30;

  //Use ACK detection mode by default
  CompatibleMode = false;

  //Activate device
  digitalWrite(AttPin, LOW);
  SPI.beginTransaction(SPISettings(250000, LSBFIRST, SPI_MODE3));

  SendCommand(0x81, 300);      //Access Memory Card
  SendCommand(0x57, 300);      //Send write command
  SendCommand(0x00, 300);      //Memory Card ID1
  SendCommand(0x00, 300);      //Memory Card ID2
  SendCommand(AddressMSB, 300);      //Address MSB
  SendCommand(AddressLSB, 300);      //Address LSB

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
    SendCommand(ReadData[i], 150);
  }

  SendCommand(Serial.read(), 200);      //Checksum (MSB xor LSB xor Data)
  SendCommand(0x00, 200);               //Memory Card ACK1
  SendCommand(0x00, 200);               //Memory Card ACK2
  Serial.write(SendCommand(0x00, 200)); //Memory Card status byte

  //Deactivate device
  digitalWrite(AttPin, HIGH);
  SPI.endTransaction();
}

void setup()
{
  //Set up serial communication
  Serial.begin(38400);

  //Set up pins
  PinSetup();
}

void loop()
{
  //Listen for commands
  if(Serial.available() > 0)
  {
    ReadByte = Serial.read();

    switch(ReadByte)
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
