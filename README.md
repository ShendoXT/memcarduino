# MemCARDuino
### Arduino PlayStation 1 Memory Card reader

## Thanks to:
* Martin Korth of the NO$PSX - documented Memory Card protocol.
* Andrew J McCubbin - documented PS1 SPI interface.

## Connecting a Memory Card to Arduino:
    Looking at the Memory Card:
    _________________
    |_ _|_ _ _|_ _ _|
     1 2 3 4 5 6 7 8

MC 1: DATA - D12 on Arduino<br>
MC 2: CMND - D11 on Arduino<br>
MC 3: 7.6V - External 7.6V power (only required for 3rd party cards and knockoffs)<br>
MC 4: GND - GND Pin on Arduino<br>
MC 5: 3.6V - 5V/3.3V Pin on Arduino<br>
MC 6: ATT - D10 on Arduino<br>
MC 7: CLK - D13 on Arduino<br>
MC 8: ACK - D2 on Arduino<br>

# Warning:
PS1 MemoryCard is a 3.6V device but (old) Arduino uses 5V logic.<br>That may shorten lifespan of your MemoryCard or damage it permanently.<br>
It is recommended to use 3.3V Arduino devices to avoid any damage to your MemoryCard.

## Reading save from a PC:
To read saves from the Memory Card to your PC use [MemcardRex](http://shendosoft.blogspot.com/2014/01/memcardrex-18-released.html) if you are using Windows.   
For other operating systems use a provided Python script.   
If you are writing your own application the protocol is as follows:   

## Interfacing with MemCARDuino:
Communication is done at **38400 bps**.    
To check if the MemCARDuino is connected to the selected COM port send **GETID** command.    
Device should respond with **IDENTIFIER**.    
Optionally you can send a **GETVER** to get the version of the firmware.    

To Read a 128byte frame send a **MCR** command with *MSB* byte and *LSB* byte of the frame you want to read.    
MemCARDduino will respond with 128 byte frame data, [MSB xor LSB xor Data] and Memory Card status byte.    

To Write a frame send a **MCW** command with *MSB* byte and *LSB* byte, 128 byte data and [MSB xor LSB xor Data].    
MemCARDduino will respond with Memory Card status byte.    

### Checking if Memory Card is connected:
Read a frame from the card and verify the returned status byte.    
If it's 0x47 then card is connected. If it's 0xFF card is not connected.    

# Python interface:
Two python scripts are designed to raw copy the Memory Card data to PC and vice versa.
memcarduino.py is Py2 Script
memcarduino_py3.py is Py3 Script    
**Note:** As usual, use at your own risk, it might not work out of the box.    

## Usage
First install pyserial 
    pip install pyserial
For Python 2    
    memcarduino.py -p,--port <serial port> , -r,--read <output file> OR -w,--write <input file> OR -f,--format , [-c,--capacity <capacity>] , [-b,--bitrate <bitrate:bps>]

    <serial port> accepts COM port names, or for linux, file references (/dev/tty[...] or others)
    <output file> read from memory card and save to file
    <input file> read from file and write to memory card (accepts both windows and linux file URI's)
    <capacyty> sets memory card capacity [blocks] *1 block = 128 B* (default 1024 blocks)
    <bitrate> sets bitrate on serial port (default 38400 bps)
For Python 3
    memcarduino_py3.py -p,--port <serial port> , -r,--read <output file> OR -w,--write <input file> OR -f,--format , [-c,--capacity <capacity>] , [-b,--bitrate <bitrate:bps>]

    <serial port> accepts COM port names, or for linux, file references (/dev/tty[...] or others)
    <output file> read from memory card and save to file
    <input file> read from file and write to memory card (accepts both windows and linux file URI's)
    <capacyty> sets memory card capacity [blocks] *1 block = 128 B* (default 1024 blocks)
    <bitrate> sets bitrate on serial port (default 38400 bps)


This requires a serial port (/dev/ttyACM0 for Arduino uno's, /dev/ttyUSBX for others, COMX for Windows, and various for macOS) it also requires a specific output file.
Changing the baudrate isn't recommended, but is available anyway (it does mean changing the Arduino code manually...)

## Python TODO:
* Read/Write individual saves
* Add a man page for the script
* Refine comments, readme and script
