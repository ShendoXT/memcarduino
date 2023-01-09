### Interfacing with MemCARDuino:

|Commands|Data|Parameters|Description|Response|
| -- | -- | -- | -- | -- |
|GETID | 0xA0 | - | Get identifier | "MCDINO"
|GETVER | 0xA1 | - | Get firmware version | Firmware version byte (Major.Minor).
|MCR | 0xA2 | MSB, LSB | Memory Card Read (frame) | Data, XOR, Status
|MCW | 0xA3 | MSB, LSB, data, XOR | Memory Card Write (frame) | Status

|Status|Data|Description|
| -- | -- | -- |
|ERROR | 0xE0 | Invalid command received (error)
|GOOD | 0x47 | Operation successful
|BAD_CHECKSUM | 0x4E | Data corruption occured
|BAD_SECTOR | 0xFF | Outside of max sector range

Communication is done at **115200 bps**.

To check if MemCARDuino is connected to the selected COM port send **GETID** command.    
Device should respond with **IDENTIFIER**.    
Optionally you can send a **GETVER** to get the version of the firmware.    

To Read a 128byte frame send a **MCR** command with *MSB* byte and *LSB* byte of the frame you want to read.    
MemCARDduino will respond with 128 byte frame data, [MSB xor LSB xor Data] and Memory Card status byte.    

To Write a frame send a **MCW** command with *MSB* byte and *LSB* byte, 128 byte data and [MSB xor LSB xor Data].    
MemCARDduino will respond with Memory Card status byte.    

### Checking if Memory Card is connected:
Read a frame from the card and verify the returned status byte.    
If it's 0x47 then card is connected. If it's 0xFF card is not connected.
