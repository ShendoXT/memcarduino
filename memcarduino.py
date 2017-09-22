#!/usr/bin/python2

#MemCARDuino python interface
#a simple command line tool for quick dumping of psx memory cards connected to a serially connected MemCARDuino project
# made by Jason D'Amico on the 28/12/2014
#	mr-fuji on 21/03/2015
#use and modification of this script is allowed, if improved do send a copy back.
#use at own risk, not my fault if burns down house or erases card (it shouldn't, but...)

import time
import serial
import sys
import array
from struct import pack
from datetime import datetime
import getopt

global GID		# get identifier
global GFV		# get firmware version
global MCR	 	# mcr read command, should be followed by a verify memcard
global MCW		# mcr write command, should be followed by a verify memcard
global MCID		# read mc identifier

global start		#first block to read from (default 0)
global end			#number of blocks to read (default 1024)
global block_size	#size (in Bytes) of each block (should remain 128)

global inputport	#input port to use
global rate			#bitrate to use
global ser			#serial
global mode			#operation

GID = "\xA0"
GFV = "\xA1"
MCR = "\xA2"
MCW = "\xA3"
MCID = "\xA4"

#cus im lazy -TheBlueTroll
#SRC: http://code.activestate.com/recipes/510399-byte-to-hex-and-hex-to-byte-string-conversion/
"""
HexByteConversion

Convert a byte string to it's hex representation for output or visa versa.

ByteToHex converts byte string "\xFF\xFE\x00\x01" to the string "FF FE 00 01"
HexToByte converts string "FF FE 00 01" to the byte string "\xFF\xFE\x00\x01"
"""

#-------------------------------------------------------------------------------

def ByteToHex( byteStr ):
    """
    Convert a byte string to it's hex string representation e.g. for output.
    """
    
    # Uses list comprehension which is a fractionally faster implementation than
    # the alternative, more readable, implementation below
    #   
    #    hex = []
    #    for aChar in byteStr:
    #        hex.append( "%02X " % ord( aChar ) )
    #
    #    return ''.join( hex ).strip()        

    return ''.join( [ "%02X " % ord( x ) for x in byteStr ] ).strip()

def help():
	print "memcarduino usage:"
	print "memcarduino.py -p,--port <serial port> , -r,--read <output file> OR -w,--write <input file> OR -f,--format , [-c,--capacity <capacity>] , [-b,--bitrate <bitrate:bps>]"
	print "<serial port> accepts COM port names, or for linux, file references (/dev/tty[...] or others)"
	print "<output file> read from memory card and save to file"
	print "<input file> read from file and write to memory card (accepts both windows and linux file URI's)"
	print "<capacyty> sets memory card capacity [blocks] *1 block = 128 B* (default 1024 blocks)"
	print "<bitrate> sets bitrate on serial port (default 38400 bps)"
	print "format command formats memorycard with all \\x00\n\n\n"

def test():
	ser.close()
	ser.open()		# sometimes when serial port is opened, the arduino resets,so open, then wait for it to reset, then continue on with the check
	time.sleep(2)
	ser.isOpen()
	
	check_connection()
def testFormat():
	ser.close()
	ser.open()		# sometimes when serial port is opened, the arduino resets,so open, then wait for it to reset, then continue on with the check
	time.sleep(2)
	ser.isOpen()
	
	#check_connection() #thows error when the first frame is erased, which format does

def check_connection():
	
	temp = ""
	#print "running mcduino check"
	#start mcduino verify 

	ser.write(GID)
	temp=ser.read(6)
	if temp !="MCDINO":
		print "error: mcduino communication error, got \""+temp + "\" as identifier (should be \"MCDINO\")\n\n"
		sys.exit()
	#end mcduino verify
	##print "passed mcduino check\nRunning mcr header check"
	#start mcr verify
	ser.write(MCR + "\x00" + chr(1))
	temp=ser.read(129)
	b = ser.read(1)

	if b!="\x47":
		print"error: mc read failure, check connections\n\n"
		sys.exit()
	#print "passed header check"
	
def memcard_read(file):
	f = file
	temp = ""
	print "reading data from memory card...\n"
	passed = 0
	for i in xrange(start, end):
		tstart = datetime.now()
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
		ser.write(hex_data[0])
		ser.write(hex_data[1])

		temp = ser.read(block_size)
		ser.read(1)
		b = ser.read(1)
		tend = datetime.now()
		tPrint=tend-tstart
		if(b == "\x47"):
			f.write(temp)
			print "OK at frame "+str(i+1)+"/"+str(end)+"  Address:"+ByteToHex(hex_data)+" TimeTaken:"+str(tPrint)
			passed += 1
		elif(b == "\x4E"):
			print "BAD CHECKSUM at frame "+str(i+1)+"/"+str(end)+"  Address:"+ByteToHex(hex_data)+" TimeTaken:"+str(tPrint)
			f.write("\x00"*128)
		elif(b == "\xFF"):
			print "BAD SECTOR at frame "+str(i+1)+"/"+str(end)+"  Address:"+ByteToHex(hex_data)+" TimeTaken:"+str(tPrint)
			f.write("\x00"*128)
		else:
			print "UNKNOWN ERROR at frame "+str(i+1)+"/"+str(end)+"  Address:"+ByteToHex(hex_data)+" TimeTaken:"+str(tPrint)  # WTF?
			f.write("\x00"*128)
		
	result(passed)

def memcard_write(file):
	f = file
	temp = ""
	print "writing data to memory card...\n"
	passed = 0
	for i in xrange(start, end):
		tstart = datetime.now()

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
		
		data_block = f.read(block_size)
		chk = ''
		chk = chr(ord(hex_data[1])^ord(hex_data[0])^int(ord(data_block[0])))
		ser.write(MCW)
		ser.write(hex_data[0])
		ser.write(hex_data[1])
		ser.write(data_block)
		ser.write(chk)
		b = ser.read(1)
		tend = datetime.now()
		#tPrint=tend-tstart
		tPrint="NotImplemented"
		if(b == "\x47"):
			print "OK at frame "+str(i+1)+"/"+str(end)+"  Address:"+ByteToHex(hex_data)+"  CHECKSUM:"+ByteToHex(chk)+" TimeTaken:"+str(tPrint)
			passed += 1
		elif(b == "\x4E"):
			print "BAD CHECKSUM at frame "+str(i+1)+"/"+str(end)+"  Address:"+ByteToHex(hex_data)+"  CHECKSUM:"+ByteToHex(chk)+" TimeTaken:"+str(tPrint)+str(res)
		elif(b == "\xFF"):
			print "BAD SECTOR at frame "+str(i+1)+"/"+str(end)+"  Address:"+ByteToHex(hex_data)+"  CHECKSUM:"+ByteToHex(chk)+" TimeTaken:"+str(tPrint)
		else:
			print "UNKNOWN ERROR at frame "+str(i+1)+"/"+str(end)+"  Address:"+ByteToHex(hex_data)+"  CHECKSUM:"+ByteToHex(chk)+" TimeTaken:"+str(tPrint)   # WTF?
			
	result(passed)
	
def memcard_format():
	temp = ""
	print "formatting memory card...\n"
	passed = 0
	for i in xrange(start, end):
		tstart = datetime.now()
		if (i==0):
			
			#how about actually not blanking the identifier frame.
			#instead, lets write it
			hex_data="\x00"+"\x00"
			data_block = "\x4D" + "\x43" #"MC"
			data_block = data_block+"\x00"*125 #125 blanks
			data_block = data_block+"\x0E" #checksum
			
			#just copy pasted the write code here
			chk = ''
			chk = chr(ord(hex_data[1])^ord(hex_data[0])^int(ord("\x00")))
			ser.write(MCW)
			ser.write(hex_data[0])
			ser.write(hex_data[1])
			ser.write(data_block)
			ser.write(chk)
			b = ser.read(1)
			tend = datetime.now()
			tPrint=tend-tstart
			if(b == "\x47"):
				print "OK at frame "+str(i+1)+"/"+str(end)+"  Address:"+ByteToHex(hex_data)+" TimeTaken:"+str(tPrint)
				passed += 1
			elif(b == "\x4E"):
				print "BAD CHECKSUM at frame "+str(i+1)+"/"+str(end)+"  Address:"+ByteToHex(hex_data)+" TimeTaken:"+str(tPrint)
			elif(b == "\xFF"):
				print "BAD SECTOR at frame "+str(i+1)+"/"+str(end)+"  Address:"+ByteToHex(hex_data)+" TimeTaken:"+str(tPrint)
			else:
				print "UNKNOWN ERROR at frame "+str(i+1)+"/"+str(end)+"  Address:"+ByteToHex(hex_data)+" TimeTaken:"+str(tPrint)   # WTF?
		else:
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
			
			data_block = "\x00"*128
			chk = ''
			chk = chr(ord(hex_data[1])^ord(hex_data[0])^int(ord("\x00")))
			ser.write(MCW)
			ser.write(hex_data[0])
			ser.write(hex_data[1])
			ser.write(data_block)
			ser.write(chk)
			b = ser.read(1)
			tend = datetime.now()
			tPrint=tend-tstart
			if(b == "\x47"):
				print "OK at frame "+str(i+1)+"/"+str(end)+"  Address:"+ByteToHex(hex_data)+" TimeTaken:"+str(tPrint)
				passed += 1
			elif(b == "\x4E"):
				print "BAD CHECKSUM at frame "+str(i+1)+"/"+str(end)+"  Address:"+ByteToHex(hex_data)+" TimeTaken:"+str(tPrint)
			elif(b == "\xFF"):
				print "BAD SECTOR at frame "+str(i+1)+"/"+str(end)+"  Address:"+ByteToHex(hex_data)+" TimeTaken:"+str(tPrint)
			else:
				print "UNKNOWN ERROR at frame "+str(i+1)+"/"+str(end)+"  Address:"+ByteToHex(hex_data)+" TimeTaken:"+str(tPrint)   # WTF?
				
	result(passed)
		
def result(passed):
	print "\n\n\n"
	if(passed == end):
		print "SUCCESS"
	else:
		print mode + " ERROR: "+str(1024-passed)+" failed\n"

#MAIN VARIABLES
start = 0
end = 1024
block_size = 128
inputport = ""
rate = 38400
file = ""
mode = ""

opts, args = getopt.getopt(sys.argv[1:] , "hfp:r:w:c:b" , [ "help" , "format" , "port=" , "read=" , "write=" , "capacity=" , "bitrate="])


#OPTIONS CHECK

print "\n\n"

for opt, arg in opts:
	#print opt
	#print arg
	if opt in ("-h" , "--help"):
		help()
		sys.exit()
	elif opt in ("-f" , "--format"):
		mode = "FORMAT"
	elif opt in ("-p" , "--port"):
		inputport = arg
	elif opt in("-r", "--read"):
		file = arg
		mode = "READ"
	elif opt in("-w", "--write"):
		file = arg
		mode = "WRITE"
	elif opt in ("-c" , "--capacity"):
		end = arg
	elif opt in("-b", "--bitrate"):
		print "warning: bitrate shuold not be changed unless necessary"
		rate = arg
	else:
		help()
		sys.exit()

if inputport == "":
	print "warning: no serial port specified"
	help()
	sys.exit()
if file == "" and (mode == "WRITE" or mode == "READ"):
	print 'warning: input/output file missing'
	help()
	sys.exit()


#BEGIN

ser = serial.Serial(port=inputport, baudrate=rate,timeout=2)

test()

if mode == "WRITE":
	f = open(file, 'rb')
	tOpStart = datetime.now()
	memcard_write(f)
	tOpEnd = datetime.now()
	f.close()
	tOpDelta=tOpEnd-tOpStart
	print "Total Time:"+str(tOpDelta)
elif mode == "READ":
	f = open(file, 'wb')
	tOpStart = datetime.now()
	memcard_read(f)
	tOpEnd = datetime.now()
	f.close()
	tOpDelta=tOpEnd-tOpStart
	print "Total Time:"+str(tOpDelta)
elif mode == "FORMAT":
	tOpStart = datetime.now()
	memcard_format()
	tOpEnd = datetime.now()
	tOpDelta=tOpEnd-tOpStart
	print "Total Time:"+str(tOpDelta)
else:
	print "warning: no operation selected"

ser.close()

