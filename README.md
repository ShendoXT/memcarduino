    Arduino PS1 Memory Card Reader - MemCARDuino, Shendo 2013 - 2015

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
     3 7.6V - External 7.6V power (Only required for 3rd party cards)
     4 GND - GND Pin on Arduino
     5 3.6V - 5V Pin on Arduino
     6 ATT - Pin 10 on Arduino
     7 CLK - Pin 13 on Arduino
     8 ACK - Pin 2 on Arduino
     
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

     ==================
     Python interface:
     ==================

	How to use the provided improvised python interface
	------------------------------------------
	The python script is a mashed together script (mostly OS inspecific) designed to raw copy the Memory Card data 
	from the physical world down to the virtual world. Note: Use at your own risk, might not work out of the box.
 
	memcarduino.py -p,--port <serial port> , -r,--read <output file> OR -w,--write <input file> OR -f,--format , [-c,--capacity <capacity>] , [-b,--bitrate <bitrate:bps>]
		
		<serial port> accepts COM port names, or for linux, file references (/dev/tty[...] or others)
		<output file> read from memory card and save to file
		<input file> read from file and write to memory card (accepts both windows and linux file URI's)
		<capacyty> sets memory card capacity [blocks] *1 block = 128 B* (default 1024 blocks)
		<bitrate> sets bitrate on serial port (default 38400 bps)
		
		format command formats memorycard with all 0x00

	This requires a serial port (/dev/ttyACM0 for Arduino uno's, /dev/ttyUSB for others, COMX for Windows, and whatever for OS X) it also requires a specific output file.
	Changing the baudrate isn't recommended, but is available anyway (it does mean reprograming the Arduino...)

	Given time, luck, and a vomit bag, you'll have a raw dump of your Memory Card.

	I get an eror with the Python script, what do i do?
	------------------------------------------
	The Python script is not perfect, and is only provided as a convience instead of having to write your own.

	Try reading the error output, in most cases it roughly defines the point of failure.
	e.g :"serial.serialutil.SerialException: could not open port X : [Errno 2] No such file or directory: '/dev/ttyACM0'"
	If you read it, it's saying that when it tried to open the linux\unix\windows\osx\ios\andriod(technically linux)\blackberry(god forbid) serial port by the name of /dev/ttyACM0 (which is usually an Arduino but it can also be /dev/ttyUSB0, or other numbers)
	could not be found, or does not exist. The fix is to double and triple check the serial port setting and make sure it's set 
	to whatever your serial port is actually defined as.
