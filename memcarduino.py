import time
import serial
import sys
import array
from struct import pack
import getopt


   inputport = ""
   outputfile = ""
   rate=38400
   try:
      opts, args = getopt.getopt(argv,"hi:r:o:",["iport=","rate=","ofile="])
   except getopt.GetoptError:
      print 'test.py -i <Serial Port> -o <outputfile>'
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print 'memcarduino.py -i <Serial Port> -o <outputfile>'
	 print '-i [--iport=] accepts COM port names, or for linux, file references (read: /dev/tty or others)'
	 print "-o[--ofile=] accepts both windows and linux file URI's,i hope" 
	 print '-r [--rate=] sets baudrate on serial port (default 38400)'
         sys.exit()
      elif opt in ("-i", "--iport"):
         inputport = arg
      elif opt in ("-o", "--ofile"):
         outputfile = arg
      elif opt in("-r","--rate");
        
   if (inputport==""):
	print 'Missing Serial Port, useage:'
	print 'memcarduino.py -i <Serial Port> -o <outputfile>'
	sys.exit()
   print 'Output file is ', outputfile
   if (outputfile==""):
	print 'output file missing, useage:'
	print 'memcarduino.py -i <Serial Port> -o <outputfile>'
	sys.exit()

ser = serial.Serial(port=inputport,baudrate=rate)
start = 0 
#for the ieterator to read all bytes of a file/memcard, set end to memory card size in bytes divided by 128
end =1024


#frankly im not sure whats this is for
def Memread():
	"read Memcard ID"
	a=ser.read(1)
	b=ser.read(1)
	c=ser.read(1)
	d=ser.read(1)
	e=ser.read(1)
	f=ser.read(1)
	g=ser.read(1)
	h=ser.read(1)


ser.close()
ser.open() #sometimes when serial port is opened, the arduino resets,so open, then wait for it to reset,
			# then continue on with the check
time.sleep(2)
ser.isOpen()

f = open(outputfile, 'w') #open file in overwrite mode, no confirm on existing file


#//Commands ripped streight from the arduino project to make coding easier
#define GETID 0xA0          //Get identifier
#define GETVER 0xA1         //Get firmware version
#define MCREAD 0xA2         //Memory Card Read (frame)
#define MCWRITE 0xA3        //Memory Card Write (frame)
#define MCID 0xA4        //Memory Card ReadID




MCR="\xA2" #mcr read command, should be  followed by a verify memcard
temp=""

for i in xrange(start, end ):
	
	if (i<=255):
		ia="\x00"+chr(i)
	else:
		ia=pack('H', i)
		ia=ia[1] +ia[0] #invert that crap on the cheap
	#convert to a 2byte hex string, then decode
	hex_data = ia
	#conv to a array
	arry=array.array('B', hex_data)
	map(ord, hex_data)
	ser.write(MCR)
	ser.write(hex_data[1])
	ser.write(hex_data[0])
	temp=ser.read(128)
	
	a=ser.read(1)
	b=ser.read(1)
	if(b!="\x47"):
		sys.stdout.write("BAD READ!") #write to terminal, if your seeing this them memcard is not returning G
	else:
		 f.write(temp)
f.close()
ser.close()
