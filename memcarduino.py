#!python3

#MemCARDuino python3 interface
#Modification of LagDav
#Notes for Python3
#### Print and Pyserial are diferent in Py2 and Py3
#### print "str" does not work in Py3 (only work in Py2) it must be changed to print (str)
#### serial.write(b"MyBytes") only accept bytes in Py3 
#### serial.write("MyString") does not work in Py3, "Mystring" must be changed to serial.write(b"MyString")
#### serial.read(int: number) is not a String, is a ByteArray.

#Original Comment of 
#a simple command line tool for quick dumping of psx memory cards connected to a serially connected MemCARDuino project
# made by Jason D'Amico on the 28/12/2014
#	mr-fuji on 21/03/2015
#	shendo on 01/07/2023 (switched to 115200 bps default)
#	shendo on 08/11/2024 (added pocketstation commands)
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

global PSINFO	# get information from pocketstation (serial, current time)
global PSBIOS	# dump bios from pocketstation
global PSTIME	# set current time to pocketstation

global start		#first frame to read from (default 0)
global end			#number of frames to read (default 1024)
global frame_size	#size (in Bytes) of each frame (should remain 128)

global inputport	#input port to use
global rate			#bitrate to use
global ser1			#serial
global mode			#operation

GID = b"\xA0"
GFV = b"\xA1"
MCR = b"\xA2"
MCW = b"\xA3"
MCID = b"\xA4"

PSINFO = b"\xB0"
PSBIOS = b"\xB1"
PSTIME = b"\xB2"

# Bytes Operators and Functions

def ByteToHex( byteStr ): # byte to hex, ex: b'\x0A' -> 0A
	return format(int.from_bytes(byteStr,byteorder='big'),'02x')

def XorElementByteArray( byteStr):  # XOR of all elemment f Byte
	result=0
	for index in range(0, len(byteStr)):
		 result=result^byteStr[index]
	return result

# Help Functions
def help():
    print("memcarduino usage:")
    print("memcarduino.py -p,--port <serial port> , -r,--read <output file> OR -w,--write <input file> OR -f,--format OR --psinfo OR --pstime OR --psbios <output file>, [-c,--capacity <capacity>] , [-b,--bitrate <bitrate:bps>]")
    print("<serial port> accepts COM port names, or for linux, file references (/dev/tty[...] or others)")
    print("<output file> read from memory card and save to file")
    print("<input file> read from file and write to memory card (accepts both windows and linux file URI's)")
    print("<capacyty> sets memory card capacity [frames] *1 frame = 128 B* (default 1024 frames)")
    print("<bitrate> sets bitrate on serial port (default 115200 bps)")
    print("format command formats memorycard with all \\x00\n")

    print("pocketstation commands:")
    print("--psinfo (print info from pocketstation)")
    print("--psbios <output file> (dump bios from pocketstation)")
    print("--pstime (appy pc time to pocketstation)\n\n\n")

# Tests Functions
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
    ser.is_open()
	
	#check_connection() #throws error when the first frame is erased, which format does

def check_connection():
    temp = ""
    print("running mcduino check")
    #start mcduino verify 
    ser.write(GID)
    temp= ser.read(6)
    if temp != b'MCDINO' :
        print ("error: mcduino communication error, got")          
        print (temp)
        print ("\" as identifier (should be \"MCDINO\")\n\n")
        sys.exit()

	#do not check frame reading for pocketstation commands
    if (mode == "PSINFO" or mode == "PSBIOS" or mode == "PSTIME"):
        return

	#test first frame
    ser.write(MCR + b"\x00\x01")
    temp=ser.read(129)
    print(temp)
    b = ser.read(1)
    print (b)
    if (b != b'\x47'):
        print("Response Byte is: \n")
        print(b)
        print("error: mc read failure, check connections\n\n")
        sys.exit()
    print ("")

# Memory Card Functions	
def memcard_read(file):
    f = file
    temp = ""
    print("reading data from memory card...\n")
    passed = 0
    for address in range(start, end):
        tstart = datetime.now()
        address_bytes =  address.to_bytes(2,byteorder='big') # integer to bytearray(2,bigendian) example 1 --> b'\x00\x01
        frame = str(address+1)
        ser.write(MCR)
        ser.write(address_bytes[0].to_bytes(1, byteorder='big')) # bytearray is bytes but bytearray[i] is int
        ser.write(address_bytes[1].to_bytes(1, byteorder='big')) # bytearray is bytes but bytearray[i] is int
        temp = ser.read(frame_size)
        ser.read(1)
        b = ser.read(1)
        tend = datetime.now()
        tPrint=tend-tstart
        #str128zeros = "\x00"*128
        #print(ByteToHex(b))
        if(b == b'\x47'):
            f.write(temp)
            print("OK at frame "+frame+"/"+str(end)+"  Address:"+ByteToHex(address_bytes)+" TimeTaken:"+str(tPrint))
            passed += 1
        elif(b == b'\x4E') :
            print("BAD CHECKSUM at frame "+frame+"/"+str(end)+"  Address:"+ByteToHex(address_bytes)+" TimeTaken:"+str(tPrint))
            f.write(b"\x00"*128)
        elif(b == b'\xFF'):
            print("BAD SECTOR at frame "+frame+"/"+str(end)+"  Address:"+ByteToHex(address_bytes)+" TimeTaken:"+str(tPrint))
            f.write(b"\x00"*128)
        else:
            print("UNKNOWN ERROR at frame "+frame+"/"+str(end)+"  Address:"+ByteToHex(address_bytes)+" TimeTaken:"+str(tPrint))  # WTF?
            f.write(b"\x00"*128)                

    result(passed)

def memcard_write(file):
	f = file
	#temp = ""
	print("writing data to memory card...\n")
	passed = 0
	for address in range(start, end):
	#	tstart = datetime.now()
		address_bytes = address.to_bytes(2,byteorder='big') # integer to bytearray(2,bigendian) example 1 --> b'\x00\x01
		frame = str(address+1)
		data_block = f.read(frame_size)
		chk = b''
		chk = address_bytes[1]^address_bytes[0]^XorElementByteArray(data_block)
		ser.write(MCW)
		ser.write(address_bytes[0].to_bytes(1, byteorder='big')) # bytearray is bytes but bytearray[i] is int
		ser.write(address_bytes[1].to_bytes(1, byteorder='big')) # bytearray is bytes but bytearray[i] is int
		ser.write(data_block)
		ser.write(chk.to_bytes(1,byteorder='big'))	
		b = ser.read(1)
	    #tend = datetime.now()
		#tPrint=tend-tstart
		tPrint="NotImplemented"
		if(b == b"\x47"):
			print("bytereceive:"+ ByteToHex(b) +"  OK at frame "+frame+"/"+str(end)+"  Address:"+ByteToHex(address_bytes)+"  CHECKSUM:"+ByteToHex(chk.to_bytes(1,byteorder='big'))+" TimeTaken:"+str(tPrint))
			passed += 1
		elif(b == b"\x4E"):
			print("bytereceive:"+ ByteToHex(b) +"  BAD CHECKSUM at frame "+frame+"/"+str(end)+"  Address:"+ByteToHex(address_bytes)+"  CHECKSUM:"+ByteToHex(chk.to_bytes(1,byteorder='big'))+" TimeTaken:"+str(tPrint))
		elif(b == b"\xFF"):
			print("bytereceive:"+ ByteToHex(b) +"  BAD SECTOR at frame "+frame+"/"+str(end)+"  Address:"+ByteToHex(address_bytes)+"  CHECKSUM:"+ByteToHex(chk.to_bytes(1,byteorder='big'))+" TimeTaken:"+str(tPrint))
		else:
			print ("bytereceive:"+ ByteToHex(b) +"  UNKNOWN ERROR at frame "+frame+"/"+str(end)+"  Address:"+ByteToHex(address_bytes)+"  CHECKSUM:"+ByteToHex(chk.to_bytes(1,byteorder='big'))+" TimeTaken:"+str(tPrint))   # WTF?
		
		#this delay here is because of the pocketstation, if data is written too fast it's gonna crash
		time.sleep(0.15)
	
	result(passed)
	
def memcard_format():
	#temp = ""
	print("formatting memory card...\n")
	passed = 0
	for address in range(start, end):
		tstart = datetime.now()
		frame = str(address+1)
		address_bytes = address.to_bytes(2,byteorder='big') # integer to bytearray(2,bigendian) example 1 --> b'\x00\x01
		if (address==0):
			data_block = b"MC" #"MC"
			data_block = data_block+(b"\x00"*125) #125 blanks
			data_block = data_block+b"\x0E" #checksum
		else:
			data_block = b"\x00"*128 	
		chk =  b""
		chk = ((address_bytes[1])^(address_bytes[0])^XorElementByteArray(data_block))
		ser.write(MCW)
		ser.write(address_bytes[0].to_bytes(1,'big')) # bytearray is bytes but bytearray[i] is int
		ser.write(address_bytes[1].to_bytes(1,'big')) # bytearray is bytes but bytearray[i] is int
		ser.write(data_block)
		ser.write(chk.to_bytes(1,byteorder='big'))
		b = ser.read(1)
		tend = datetime.now()
		tPrint=tend-tstart
		if(b == b"\x47"):
			print("OK at frame "+frame+"/"+str(end)+"  Address:"+ByteToHex(address_bytes)+" TimeTaken:"+str(tPrint))
			passed += 1
		elif(b == b"\x4E"):
			print("BAD CHECKSUM at frame "+frame+"/"+str(end)+"  Address:"+ByteToHex(address_bytes)+" TimeTaken:"+str(tPrint))
		elif(b == b"\xFF"):
			print("BAD SECTOR at frame "+frame+"/"+str(end)+"  Address:"+ByteToHex(address_bytes)+" TimeTaken:"+str(tPrint))
		else:
			print("UNKNOWN ERROR at frame "+frame+"/"+str(end)+"  Address:"+ByteToHex(address_bytes)+" TimeTaken:"+str(tPrint))   # WTF?
				
	result(passed)
		
def no_pocketstation():
	print("pocketstation not found")

def ps_info():
	print("pocketstation info:")
	ser.write(PSINFO)
	b = ser.read(1)

	if(b[0] != 0x12):
		no_pocketstation()
		return

	b = ser.read(0x12)

	psserial = b[6] | b[7] << 8 | b[8] << 16

	print("serial:", end = " ")
	print(chr(b[9]), end = "")
	print("%08d" % (psserial))

	print("date:", end = " ")
	print(format(b[13], 'x'), end = "")
	print(format(b[12], 'x'), end = "/")
	print(format(b[11], 'x'), end = "/")
	print(format(b[10], 'x'))

	print("time:", end = " ")
	print(format(b[16], 'x'), end = ":")
	print(format(b[15], 'x'))

	print("day:", end = " ")

	if(b[17] == 1):
		print("sunday")
	elif(b[17] == 2):
		print("monday")
	elif(b[17] == 3):
		print("tuesday")
	elif(b[17] == 4):
		print("wednesday")
	elif(b[17] == 5):
		print("thursday")
	elif(b[17] == 6):	
		print("friday")
	elif(b[17] == 7):
		print("saturday")

def ps_bios(file):
	print("dump pocketstation bios:")
	f = file
	passed = 0
	checksum = 0

	for address in range(0, 128):
		tstart = datetime.now()
		frame = str(address+1)
		ser.write(PSBIOS)
		ser.write(address.to_bytes(1))

		#parameter check
		b = ser.read(1)
		if(b[0] != 0x5):
			no_pocketstation()
			sys.exit()

		#datasize check
		b = ser.read(1)
		if(b[0] != 0x80):
			no_pocketstation()
			sys.exit()

		#get bios data
		temp = ser.read(128)

		#calculate checksum
		for index in range(0, 32):
			checksum += temp[index*4] | temp[index*4 + 1] << 8| temp[index*4 + 2] << 16 | temp[index*4 + 3] << 24

		b = ser.read(1)
		tend = datetime.now()
		tPrint=tend-tstart

		if(b == b'\x47'):
			f.write(temp)
			print("OK at frame "+frame+"/128 TimeTaken:"+str(tPrint))
			passed += 1

	checksum &= 0xFFFFFFFF
	print("checksum: %08x" % (checksum))

	#check if this is a known or maybe a bad dump
	if(checksum == 0x27E94C07):
		print("1st release")
	elif(checksum == 0xB16CE96C):
		print("2nd release")
	elif(checksum == 0x1BABAF29):
		print("dtl-h4000")
	else:
		print("unknown or bad dump, redump to verify")

def get_bcd(value):
	tens = value // 10
	single = value - (tens * 10)

	return ((tens << 4) | single)

def ps_time():
	print("set pocketstation time:")

	ser.write(PSTIME)

	#parameter check
	b = ser.read(1)
	if(b[0] != 0x0):
		no_pocketstation()
		return

	#datasize check
	b = ser.read(1)
	if(b[0] != 0x8):
		no_pocketstation()
		return

	time_data = [get_bcd(datetime.now().day),
		get_bcd(datetime.now().month),
		get_bcd(datetime.now().year % 100),
		get_bcd(datetime.now().year // 100),
		get_bcd(datetime.now().second),
		get_bcd(datetime.now().minute),
		get_bcd(datetime.now().hour),
		get_bcd((datetime.now().weekday() + 2) % 7)]

	#push data to pocketstation
	ser.write(bytearray(time_data))

	print(datetime.now())

def result(passed):
	print("\n\n\n")
	if(passed == end):
		print("SUCCESS")
	else:
		print(mode + " ERROR: "+str(1024-passed)+" failed\n")

#MAIN VARIABLES
start = 0
end = 1024
frame_size = 128
inputport = ""
rate = 115200
file = ""
mode = ""

opts, args = getopt.getopt(sys.argv[1:] , "hfp:r:w:c:b" , [ "help" , "format" , "port=" , "read=" , "write=" , "capacity=" , "bitrate=", "psinfo", "psbios=", "pstime"])


#OPTIONS CHECK

print("\n\n")

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
		print("warning: bitrate should not be changed unless necessary")
		rate = arg
	elif opt in("--psinfo"):
		mode = "PSINFO"
	elif opt in("--psbios"):
		file = arg
		mode = "PSBIOS"
	elif opt in("--pstime"):
		mode = "PSTIME"
	else:
		help()
		sys.exit()

if inputport == "":
	print("warning: no serial port specified")
	help()
	sys.exit()
if file == "" and (mode == "WRITE" or mode == "READ" or mode == "PSBIOS"):
	print('warning: input/output file missing')
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
	print("Total Time:"+str(tOpDelta))
elif mode == "READ":
	f = open(file, 'wb')
	tOpStart = datetime.now()
	memcard_read(f)
	tOpEnd = datetime.now()
	f.close()
	tOpDelta=tOpEnd-tOpStart
	print("Total Time:"+str(tOpDelta))
elif mode == "FORMAT":
	tOpStart = datetime.now()
	memcard_format()
	tOpEnd = datetime.now()
	tOpDelta=tOpEnd-tOpStart
	print("Total Time:"+str(tOpDelta))
elif mode == "PSINFO":
	ps_info()
elif mode == "PSBIOS":
	f = open(file, 'wb')
	tOpStart = datetime.now()
	ps_bios(f)
	tOpEnd = datetime.now()
	f.close()
	tOpDelta=tOpEnd-tOpStart
	print("Total Time:"+str(tOpDelta))
elif mode == "PSTIME":
	ps_time()
else:
	print("warning: no operation selected")

ser.close()
