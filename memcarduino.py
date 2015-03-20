#!/usr/bin/python2

#MemCARDuino python interface
#a simple command line tool for quick dumping of psx memory cards connected to a serially connected MemCARDuino project
# made by Jason D'Amico on the 28/12/2014
#use and modification of this script is allowed, if improved do send a copy back.
#use at own risk, not my fault if burns down house or erases card (it shouldnt, but...)
import time
import serial
import sys
import array
from struct import pack
import getopt




inputport = ""
outputfile = ""
inputfile = ""
rate = 38400
opts, args = getopt.getopt(sys.argv[1:], "hp:r:i:o:", ["iport=", "rate=", "ifile=", "ofile="])
for opt, arg in opts:
	print opt
	print arg
	if opt == '-h':
		print 'memcarduino.py <Serial Port>  <outputfile>'
		print '<Serial Port> accepts COM port names, or for linux, file references (read: /dev/tty or others)'
		print "<outputfile> accepts both windows and linux file URI's,i hope"
		print "<inputfile> accepts both windows and linux file URI's,i hope"
		print '-r [--rate=] sets baudrate on serial port (default 38400)'
		sys.exit()
	elif opt =="-p" :
		inputport = arg
	elif opt=="--iport":
		inputport = arg
	elif opt =="-o":
		outputfile = arg
	elif opt == "--ofile":
		outputfile = arg
	elif opt =="-i":
		inputfile = arg
	elif opt == "--ifile":
		inputfile = arg
	elif opt in("-r", "--rate"):
		print "WARNING RATE SHOULD NOT BE CHANGED UNLESS NESSARY!!"
		rate = arg
		
if (inputport == ""):
	print 'Missing Serial Port, useage:'
	print 'memcarduino.py -p <Serial Port> -o <outputfile> [-r <baudrate>]'
	print 'OR memcarduino.py -p <Serial Port> -i <inputfile> [-r <baudrate>]'
	print 'use -h for help'
	sys.exit()
if (outputfile == "") and (inputfile == ""):
	print 'input/output file missing, useage:'
	print 'memcarduino.py -p <Serial Port> -o <outputfile> [-r <baudrate>]'
	print 'OR memcarduino.py -p <Serial Port> -i <inputfile> [-r <baudrate>]'
	print 'use -h for help'
	sys.exit()

ser = serial.Serial(port=inputport, baudrate=rate,timeout=2)
start = 0
#what to read of the memorycard, 0 to 1024 is the full 128kb of a offical sony memory card, if using 3rd party
# that has higher capacity, take the capacity and divide it by 128, e.g 128kb/128==1kb==1024
end = 1024




ser.close()
ser.open()  # sometimes when serial port is opened, the arduino resets,so open, then wait for it to reset,
						# then continue on with the check
time.sleep(2)
ser.isOpen()




# //Commands ripped streight from the arduino project to make coding easier
# define GETID 0xA0		  //Get identifier
# define GETVER 0xA1		 //Get firmware version
# define MCREAD 0xA2		 //Memory Card Read (frame)
# define MCWRITE 0xA3		//Memory Card Write (frame)
# define MCID 0xA4		//Memory Card ReadID




MCR = "\xA2"  # mcr read command, should be  followed by a verify memcard
MCW = "\xA3"  # mcr write command, should be  followed by a verify memcard
temp = ""
print "running mcduino check"
#start mcduino verify 

ser.write("\xA0")
temp=ser.read(6)
if temp !="MCDINO":
	print "mcduino communication error, expected MCDINO, got "+temp
	sys.exit()
#end mcduino verify
print "passed mcduino check\nRunning mcr header check"
#start mcr verify
ser.write(MCR+"\x00" + chr(1))
temp=ser.read(129)
b = ser.read(1)

if b!="\x47":
	print"mc read failure, check connections"
	sys.exit()
print "passed header check"

if(inputfile != ""):
	f = open(inputfile, 'rb')
elif(outputfile != ""):
	f = open(outputfile, 'wb')
	
# open file in overwrite mode, no confirm on existing file
# start of hacky black magic, if you dont understand it, DONT TOUCH IT!

passed = 0

if(inputfile != ""):
	print "starting write"
	for i in xrange(start, end):

		if (i <= 255):
			ia = "\x00" + chr(i)
		else:
			ia = pack('H', i)
			ia = ia[1] + ia[0]  # invert that crap on the cheap
		# convert to a 2byte hex string, then decode
		hex_data = ia
		# conv to a array
		arry = array.array('B', hex_data)
		map(ord, hex_data)
		# end of black magic
		
		#load data from file, 128B at a time
		data_block = f.read(128)
		chk = ''
		chk = chr(ord(hex_data[1])^ord(hex_data[0])^int(ord(data_block[0])))
		ser.write(MCW)
		ser.write(hex_data[1])
		ser.write(hex_data[0])
		ser.write(data_block)
		ser.write(chk)
		b = ser.read(1)
		if(b == "\x47"):
			sys.stdout.write("OK")  # G, for Good(read)
			passed += 1
		elif(b == "\x4E"):
			sys.stdout.write("BAD CHECKSUM")
		elif(b == "\xFF"):
			sys.stdout.write("BAD SECTOR")
		else:
			sys.stdout.write("UNKNOWN ERROR")		 
		sys.stdout.write(" at frame "+str(i+1)+"/"+str(end)+'\n')
		sys.stdout.flush()

elif(outputfile != ""):
	print "starting dump"
	for i in xrange(start, end):

		if (i <= 255):
			ia = "\x00" + chr(i)
		else:
			ia = pack('H', i)
			ia = ia[1] + ia[0]  # invert that crap on the cheap
		# convert to a 2byte hex string, then decode
		hex_data = ia
		# conv to a array
		arry = array.array('B', hex_data)
		map(ord, hex_data)
		# end of black magic
		ser.write(MCR)
		ser.write(hex_data[1])
		ser.write(hex_data[0])
		temp = ser.read(128)
		ser.read(1)
		b = ser.read(1)
		if(b == "\x47"):
			f.write(temp)
			sys.stdout.write("OK")  # G, for Good(read)
			passed += 1
		elif(b == "\x4E"):
			sys.stdout.write("BAD CHECKSUM")
		elif(b == "\xFF"):
			sys.stdout.write("BAD SECTOR")
		else:
			sys.stdout.write("UNKNOWN ERROR")   # WTF?
		sys.stdout.write(" at frame "+str(i+1)+"/"+str(end) + "\n")
		sys.stdout.flush()

f.close()
ser.close()

print "\n\n\n"

if(passed == 1024):
	print "SUCCESS"
else:
	print "ERROR: "+str(1024-passed)+" failed\n"