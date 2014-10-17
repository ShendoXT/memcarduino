/*  
    Arduino PS1 Memory Card Reader - MemCARDuino, Shendo 2013

    Thanks to:
    Martin Korth of the NO$PSX - documented Memory Card protocol.
    Andrew J McCubbin - documented PS1 SPI interface.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see http://www.gnu.org/licenses.

    Connecting a Memory Card to Arduino:
    ------------------------------------
    Looking at the Memory Card:
    _________________
    |_ _|_ _ _|_ _ _|
     1 2 3 4 5 6 7 8
     
     1 DATA - Pin 12 on Arduino
     2 CMND - Pin 11 on Arduino
     3 7.6V - 5V Pin on Arduino
     4 GND - GND Pin on Arduino
     5 3.6V - 5V Pin on Arduino
     6 ATT - Pin 10 on Arduino
     7 CLK - Pin 13 on Arduino
     8 ACK - Pin 2 on Arduino
     
     If your card still isn't readable and it's a 3rd party card,
     you will need to supply it with 7.6 V extrenal power supply.
     
     Interfacing a MemCARDuino:
     ---------------------------
     Communication is done at 38400 bps.
     To check if the MemCARDuino is connected to the selected COM port send a GETID command.
     Device should respond with IDENTIFIER.
     Optionally you can send a GETVER to get the version of the firmware.
     
     To Read a 128byte frame send a MCR command with MSB byte and LSB byte of the frame you want to read.
     MemCARDduino will respond with 128 byte frame data, [MSB xor LSB xor Data] and Memory Card status byte.
     
     To Write a frame send a MCW command with MSB byte and LSB byte, 128 byte data and [MSB xor LSB xor Data].
     MemCARDduino will respond with Memory Card status byte.
     
     Checking if the Memory Card is inserted:
     -----------------------------------------
     Read a frame of the card and verify the returned status byte.
     If it's 0x47 then card is connected. If it's 0xFF card is not connected.
*/

#include "Arduino.h"

//Device Firmware identifier
#define IDENTIFIER "MCDINO"  //MemCARDuino
#define VERSION 0x02         //Firmware version byte (Major.Minor)

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
#define DataPin 12         //Data
#define CmdPin 11          //Command
#define AttPin 10          //Attention (Select)
#define ClockPin 13        //Clock
#define AckPin 2           //Acknowledge

byte ReadByte = 0;

//Set up pins for communication
void PinSetup()
{
  byte clr = 0;
  
  pinMode(DataPin, INPUT);
  pinMode(CmdPin, OUTPUT);
  pinMode(AttPin, OUTPUT);
  pinMode(ClockPin, OUTPUT);
  pinMode(AckPin, INPUT);
  
  //Set up SPI on Arduino (250 kHz, clock active when low, reading on falling edge of the clock)
  SPCR = 0x7F;
  clr=SPSR;
  clr=SPDR;
  
  digitalWrite(DataPin, HIGH);    //Activate pullup resistor
  digitalWrite(CmdPin, LOW);
  digitalWrite(AttPin, HIGH);
  digitalWrite(ClockPin, HIGH);
  digitalWrite(AckPin, HIGH);    //Activate pullup resistor
}

//Send a command to PlayStation port using SPI
byte SendCommand(byte CommandByte, int Delay)
{
    SPDR = CommandByte;             // Start the transmission
    while (!(SPSR & (1<<SPIF)))     // Wait for the end of the transmission
    {
    };
    
    //Wait for the ACK signal from the Memory Card for preset delay
    while((PORTD & 4) > 0)
    {
      Delay--;
      delayMicroseconds(1);
      if(Delay == 0)break;
    }
    
  return SPDR;                    // return the received byte
}

//Read a frame from Memory Card and send it to serial port
void ReadFrame(byte AddressMSB, byte AddressLSB)
{
  //Activate device
  PORTB &= 0xFB;    //Set pin 10 (AttPin, LOW)
  
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
  PORTB |= 4;    //Set pin 10 (AttPin, HIGH)
}

//Write a frame from the serial port to the Memory Card
void WriteFrame(byte AddressMSB, byte AddressLSB)
{
  byte ReadData[128];
  int DelayCounter = 30;

  //Activate device
  PORTB &= 0xFB;    //Set pin 10 (AttPin, LOW)
  
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
  SendCommand(0x00, 200);      //Memory Card ACK1
  SendCommand(0x00, 200);      //Memory Card ACK2
  Serial.write(SendCommand(0x00, 200));      //Memory Card status byte
  
  //Deactivate device
  PORTB |= 4;    //Set pin 10 (AttPin, HIGH)
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
      ReadFrame(Serial.read(), Serial.read());
        break;
        
      case MCWRITE:
      delay(5);
      WriteFrame(Serial.read(), Serial.read());
        break;
    }
  }
}



