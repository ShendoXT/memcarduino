#MemCARDuino python interface
#a simple command line tool for quick dumping of psx memory cards connected to a serially connected MemCARDuino project
# made by Jason D'Amico on the 28/12/2014
#use and modification of this script is allowed, if improved do send a copy back
import time
import serial
import sys
import array
from struct import pack

#serial port settings
ser = serial.Serial(port='/dev/ttyACM0',baudrate=38400)

#what to read of the memorycard, 0 to 1024 is the full 128kb of a offical sony memory card, if using 3rd party
# that has higher capacity, take the capacity and divide it by 128, e.g 128kb/128==1kb==1024
start = 0
end =1024
#memcarduino read memory card command, DONT CHANGE THIS
MCR="\xA2"


ser.close()
ser.open()
ser.isOpen()



for i in xrange(start, end ):
	
	if (i<=255):
		ia="\x00"+chr(i) #for less then 256 do it easy,
	else:
		ia=pack('H', i) #for greater then 256 screw around abit
		ia=ia[1] +ia[0] #invert it before decoding it
	
	hex_data = ia
	arry=array.array('B', hex_data)#Dont even ask what black magic is going on here, only know it works.
	map(ord, hex_data)
	ser.write(MCR)
	ser.write(hex_data[1])#invert it as it comes out, 'but why dont you just not invert it as it goes in', because the black magic
	ser.write(hex_data[0])#breaks if i do that, so i dont do that, it still gives working card dumps, so live with it
	temp=ser.read(128)
	
	a=ser.read(1)#a holds the "checksum" byte, which i just ignore because i can
	b=ser.read(1)#b holds the memorycard's "was the read successful" byte, if its not ancii G for good, then complain
	if(b!="\x47"):
		sys.stdout.write("BAD READ!")
	else:
		 sys.stdout.write(temp)#else write it out and continue living, if you get BAD READ! then check the cards connected, and that its wired right.
ser.close()
