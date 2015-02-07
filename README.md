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

    All comments below are solely the opinion of TheBlueTroll, and as such should be taken very lightly 

    How to use the provided Improvised python interface
    ------------------------------------------
    The python script is a mashed together script designed to raw copy the memory card on a os that doesnt have
    Win, Dows, Com, or other propietary nonsense. essentially a linux jerryrig (with the added bonus of being mostly OS inspecific) to get your memory cards from the 
    Physical world down to the virtual world,(use at own risk, might not work out of box).
 
    python memcarduino.py -i <Serial Port> -o <outputfile> [-r <baudrate>]

    this requires a serial port (/dev/ttyACM0 for arduino uno's, /dev/ttyUSB for others, COM1-COM4 for windoze, and whatever for macs)
    it also requires a specific output file.
    changing the baudrate isnt recommended, but is available anyway (it does mean reporgraming the arduino...)

    given time, luck, and a vomit bag, you'll have a raw dump of your memory card.

    I Get A Error With The Python script, What do i Do?
    ------------------------------------------
    The Python script is not perfect, and is only provided as a convience instead of having to write your own,
    also try this thing called "READING", because most to all times it helps figure out the issue. 
    e.g :"serial.serialutil.SerialException: could not open port X : [Errno 2] No such file or directory: '/dev/ttyACM0'"
    if you read it, its saying that when it tried to open the linux\unix\windoze\mac\ios\andriod(technically linux)\blackberry(god forbid) serial port by the name of /dev/ttyACM0 (which is usually a arduino, can also be /dev/ttyUSB0, or other numbers)
    it could not be found, or does not exist, the fix is to double and triple check the serial port setting and make sure its set 
    to whatever your serial port is actually defined as. its that easy!

    'I can do a better job of that python script with 1 arm tied behind my back!', well good, feel free to actually
    improve upon it, be sure to send a copy back.
    

