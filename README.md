# MemCARDuino
### Arduino PlayStation 1 Memory Card reader
![memcarduino](https://github.com/ShendoXT/memcarduino/blob/master/Images/memcarduino.jpg)

## Supported platforms:
* Arduino Uno, Duemilanove, Diecimila, Nano, Mini, Fio (ATmega168/P or ATmega328/P)
* Arduino Leonardo, Micro (ATmega32U4)
* Arduino Mega 2560
* Espressif [ESP8266](https://github.com/esp8266/Arduino), [ESP32](https://github.com/espressif/arduino-esp32) (requires additional board URL)
* [Raspberry Pi Pico](https://github.com/earlephilhower/arduino-pico) (requires additional board URL)

Various other boards can be supported if they have Arduino core available with SPI library with minimal or no editing to the sketch.
## Connecting a Memory Card to Arduino:
    Looking at the Memory Card:
    _________________
    |_ _|_ _ _|_ _ _|
     1 2 3 4 5 6 7 8
     
| Memory Card   | Uno, Nano, etc| Leonardo, Micro| Mega 2560 | ESP8266 | ESP32 | Pi Pico |
| ------------- | ------------- |--| -- | -- | -- | -- |
|1: Data | D12 | ICSP MISO | D50 | GPIO12 (D6)| GPIO19 | GP16
|2: Command | D11 | ICSP MOSI | D52 | GPIO13 (D7)| GPIO23 | GP19
|3: 7.6V | See 7.6V note | See 7.6V note | See 7.6V note | See 7.6V note | See 7.6V note | See 7.6V note
|4: Gnd  | Gnd | Gnd | Gnd | Gnd | Gnd | Gnd
|5: 3.6V | See VCC note | 3.3V | 3.3V | 3.3V | 3.3V | 3.3V
|6: Attention  | D10 | D10 | D53 | GPIO15 (D8) | GPIO5 | GP17
|7: Clock  | D13 | ICSP SCK | D52 | GPIO14 (D5) | GPIO18 | GP18
|8: Acknowledge  | D2 | D2 | D2 | GPIO2 (D4) | GPIO22 | GP20

**VCC note:** Memory Card is a 3.6V device. Connect it to either 3.3V provided by the board or use external 3.6 power supply.<br>
Old Arduino uses 5V logic and it is not recommended. It may shorten lifespan of your MemoryCard or damage it permanently.

**7.6V note:** This is only required for 3rd party Memory Cards and knockoffs.<br>
Use external 7.6V power supply or if you are lucky you can get by with using 5V provided by the USB.

## Reading saves from a PC:
To read saves from the Memory Card to your PC use [MemcardRex](https://github.com/ShendoXT/memcardrex/releases) if you are using Windows.<br>
Make sure to use the latest version because MemCARDuino now runs at 115200bps while older releases used 38400bps.

For other operating systems you can use a provided Python script.

Before using install pyserial:

    pip3 install pyserial
Usage:

    python3 memcarduino.py -p,--port <serial port> , -r,--read <output file> OR -w,--write <input file> OR -f,--format , [-c,--capacity <capacity>] , [-b,--bitrate <bitrate:bps>]

    <serial port> accepts COM port names, or for linux, file references (/dev/tty[...] or others)
    <output file> read from memory card and save to file
    <input file> read from file and write to memory card (accepts both windows and linux file URI's)
    <capacyty> sets memory card capacity [blocks] *1 block = 128 B* (default 1024 blocks)
    <bitrate> sets bitrate on serial port (default 115200 bps)

This requires a serial port (/dev/ttyACM0 for Arduino uno's, /dev/ttyUSBX for others, COMX for Windows, and various for macOS).

## Thanks to:
* Martin Korth of the NO$PSX - documented Memory Card protocol.
* Andrew J McCubbin - documented PS1 SPI interface.
