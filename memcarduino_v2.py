#!/usr/bin/python3

import serial
import time
import struct
import sys
import os
from enum import Enum, EnumMeta

# MemCARDuino interface V2
# Full rewrite in Python 3
# Made by krzys_h on 2019-07-24

FRAME_SIZE = 128
FRAME_COUNT = 1024

class MemcarduinoCmd(Enum):
	GID = b"\xA0"  # get identifier
	GFV = b"\xA1"  # get firmware version
	MCR = b"\xA2"  # mcr read command, should be followed by a verify memcard
	MCW = b"\xA3"  # mcr write command, should be followed by a verify memcard
	MCID = b"\xA4"  # read mc identifier

class MemcardStatusCodeMeta(EnumMeta):
	# Generates a UNKNOWN_xx enum value for all undefined bytes
	def __new__(metacls, cls, bases, classdict):
		unknowns = list(range(256))
		enum_members = {k: classdict[k] for k in classdict._member_names}
		for k in classdict._member_names:
			unknowns.remove(classdict[k])
		for u in unknowns:
			name = "UNKNOWN_%02X" % u
			classdict[name] = u
		return super().__new__(metacls, cls, bases, classdict)

	def __call__(self, x):
		if type(x) == bytes or type(x) == str:
			if len(x) != 1:
				raise ValueError("String of length != 1 detected")
			x = x[0]
		if type(x) != int:
			x = ord(x)
		return super().__call__(x)

class MemcardStatusCode(Enum, metaclass=MemcardStatusCodeMeta):
	GOOD = ord("G")
	BAD_CHECKSUM = ord("N")
	NO_CARD = ord("\xff")

class MemcarduinoException(Exception):
	pass

class Memcarduino:
	def __init__(self, **kwargs):
		self.ser = serial.Serial(**kwargs)
		time.sleep(1) # wait because arduino restarts
		self.check_conn()

	def close(self):
		self.ser.close()

	def check_conn(self):
		# Send ID check
		self.ser.write(MemcarduinoCmd.GID.value)
		identifier = self.ser.read(6)
		if identifier != b"MCDINO":
			raise MemcarduinoException("Communication error, got \"{}\" as identifier (should be \"MCDINO\")".format(identifier))

	def check_card(self):
		# Try read frame 1 to check if memory card is plugged in
		self.ser.write(MemcarduinoCmd.MCR.value + b"\x00\x01")
		self.ser.read(FRAME_SIZE) # data
		self.ser.read(1) # checksum
		status = MemcardStatusCode(self.ser.read(1))
		if status != MemcardStatusCode.GOOD:
			raise MemcarduinoException("Read failure ({}), check connections".format(status.name))

	def fw_version(self):
		self.ser.write(MemcarduinoCmd.GID.value)
		identifier = self.ser.read(6)
		self.ser.write(MemcarduinoCmd.GFV.value)
		version = struct.unpack('B', self.ser.read(1))[0]
		return identifier, version

	def fw_version_str(self):
		identifier, version = self.fw_version()
		version_major = (version >> 4) & 0x0f
		version_minor = version & 0x0f
		return "{} {}.{}".format(identifier.decode(), version_major, version_minor)

	def read_frame(self, frame_number, verify_checksums=True):
		frame_number_bytes = struct.pack('>H', frame_number)
		assert len(frame_number_bytes) == 2
		self.ser.write(MemcarduinoCmd.MCR.value + frame_number_bytes)
		data = self.ser.read(FRAME_SIZE)
		assert len(data) == FRAME_SIZE
		checksum = struct.unpack('>B', self.ser.read(1))[0]
		status = MemcardStatusCode(self.ser.read(1))
		if status != MemcardStatusCode.GOOD:
			raise MemcarduinoException("Read error: {}".format(status.name))
		if verify_checksums:
			my_checksum = Memcarduino.checksum(frame_number_bytes + data)
			if my_checksum != checksum:
				raise MemcarduinoException("Checksum mismatch, got 0x%02X should be 0x%02X" % (my_checksum, checksum))
		return data

	def write_frame(self, frame_number, data):
		assert len(data) == FRAME_SIZE
		frame_number_bytes = struct.pack('>H', frame_number)
		assert len(frame_number_bytes) == 2
		self.ser.write(MemcarduinoCmd.MCW.value + frame_number_bytes)
		self.ser.write(data)
		my_checksum = Memcarduino.checksum(frame_number_bytes + data)
		self.ser.write(struct.pack('>B', my_checksum))
		status = MemcardStatusCode(self.ser.read(1))
		if status != MemcardStatusCode.GOOD:
			raise MemcarduinoException("Write error: {}".format(status.name))

	@staticmethod
	def checksum(data):
		my_checksum = 0
		for byte in data:
			my_checksum ^= byte
		return my_checksum

if __name__ == "__main__":
	import argparse
	import binascii
	import serial.tools.list_ports

	parser = argparse.ArgumentParser(description="The commandline interface for MemCARDuino, version 2")
	parser.add_argument("-p", "--port", help="the COM port MemCARDuino is attached to, e.g. COM5 or /dev/ttyACM0")
	parser.add_argument("-b", "--baud", help="the baud rate to use, don't touch unless you know what you are doing. Defaults to 38400", default=38400)
	parser.add_argument("-c", "--capacity", help="override the card capacity in frames (frame = 128 bytes), don't touch unless you know what you are doing. Defaults to {}".format(FRAME_COUNT), default=FRAME_COUNT, type=int)
	parser.add_argument("-i", "--ignore-checksum", help="don't verify the checksums while reading", action="store_true")
	action_group = parser.add_argument_group("actions", "Select one of the actions to execute, or none to just check the connection")
	action = action_group.add_mutually_exclusive_group()
	action.add_argument("-r", "--read", help="dump the whole card to a file")
	action.add_argument("-z", "--zero", help="completely clear the card by writing 0xFF everywhere", action="store_true")
	action.add_argument("-f", "--quick-format", help="format the card, by rewriting filesystem headers", action="store_true")
	action.add_argument("-F", "--format", help="format the card, clearing all data", action="store_true")
	action.add_argument("-w", "--write", help="write a dump file to the card")
	action.add_argument("-v", "--verify", help="verify the memcard contents match a dump file")
	args = parser.parse_args()

	if not args.port:
		ports = serial.tools.list_ports.comports(include_links=False)
		if len(ports) == 1:
			args.port = ports[0].device
			print("No port specified, defaulting to " + args.port)
		else:
			print("No port specified, please use --port option")
			print("Available ports:")
			for port in ports:
				print(port.device)
			sys.exit(1)

	mc = Memcarduino(port=args.port, baudrate=args.baud)
	success = True
	try:
		print("Connected to " + mc.fw_version_str())
		mc.check_card()

		if args.read:
			f = open(args.read, "wb")
			for num in range(args.capacity):
				sys.stdout.write("\r{} / {} frames read".format(num, args.capacity))
				sys.stdout.flush()
				try:
					data = mc.read_frame(num, verify_checksums=not args.ignore_checksum)
				except MemcarduinoException as e:
					sys.stdout.write("\rError in frame {}: {}\n".format(num, str(e)))
					data = b"\x00" * FRAME_SIZE
				f.write(data)
			f.close()
			sys.stdout.write("\rDone! Written card to {}\n".format(args.read))
			sys.stdout.flush()

		if args.zero:
			for num in range(args.capacity):
				sys.stdout.write("\r{} / {} frames cleared".format(num, args.capacity))
				sys.stdout.flush()
				try:
					mc.write_frame(num, b"\xFF" * FRAME_SIZE)
				except MemcarduinoException as e:
					sys.stdout.write("\rError in frame {}: {}\n".format(num, str(e)))
				sys.stdout.write("\rDone! Card cleared       \n")
				sys.stdout.flush()

		if args.quick_format or args.format:
			# http://problemkaputt.de/psx-spx.htm#memorycarddataformat
			data = []
			def checksum_block(block):
				return block + struct.pack('B', Memcarduino.checksum(block))
			data.append(checksum_block(b"MC" + b"\x00" * 125))  # Header Frame
			for i in range(15):
				data.append(checksum_block(b"\xA0\x00\x00\x00" + b"\x00\x00\x00\x00" + b"\xFF\xFF" + b"\x00" * 21 + b"\x00" + b"\x00" * 95))  # Directory Frames
			for i in range(20):
				data.append(checksum_block(b"\xFF\xFF\xFF\xFF" + b"\x00\x00\x00\x00" + b"\xFF\xFF" + b"\x00" * 117))  # Broken Sector List
			for i in range(20):
				data.append(b"\xFF" * 128)  # Broken Sector Replacement Data
			for i in range(7):
				data.append(b"\xFF" * 128)  # Unused Frames
			data.append(checksum_block(b"MC" + b"\x00" * 125))  # Write Test Frame

			to_write = len(data)
			if not args.quick_format:
				to_write = args.capacity
			ok = True
			for num in range(to_write):
				sys.stdout.write("\r{} / {} frames formatted".format(num, to_write))
				sys.stdout.flush()
				try:
					if num < len(data):
						mc.write_frame(num, data[num])
					else:
						mc.write_frame(num, b"\xFF" * FRAME_SIZE)
				except MemcarduinoException as e:
					sys.stdout.write("\rError in frame {}: {}\n".format(num, str(e)))
					ok = False
					break
			if ok:
				sys.stdout.write("\rDone! Card reformatted       \n")
				sys.stdout.flush()
			else:
				print("Error, abort")
				success = False
			

		if args.write:
			f = open(args.write, "rb")
			f.seek(0, os.SEEK_END)
			size = f.tell()
			f.seek(0, os.SEEK_SET)
			if size != args.capacity * FRAME_SIZE:
				raise MemcarduinoException("Invalid image size, should be {} bytes, got {} bytes".format(args.capacity * FRAME_SIZE, size))
			ok = True
			for num in range(args.capacity):
				sys.stdout.write("\r{} / {} frames written".format(num, args.capacity))
				sys.stdout.flush()
				data = f.read(FRAME_SIZE)
				try:
					mc.write_frame(num, data)
				except MemcarduinoException as e:
					sys.stdout.write("\rError in frame {}: {}\n".format(num, str(e)))
					ok = False
					break
			f.close()
			if ok:
				sys.stdout.write("\rDone! Written {} to card\n".format(args.write))
				sys.stdout.flush()
			else:
				print("Error, abort")
				success = False

		if args.verify:
			f = open(args.verify, "rb")
			f.seek(0, os.SEEK_END)
			size = f.tell()
			f.seek(0, os.SEEK_SET)
			if size != args.capacity * FRAME_SIZE:
				raise MemcarduinoException("Invalid image size, should be {} bytes, got {} bytes".format(args.capacity * FRAME_SIZE, size))
			ok = True
			for num in range(args.capacity):
				sys.stdout.write("\r{} / {} frames verified".format(num, args.capacity))
				sys.stdout.flush()
				data_file = f.read(FRAME_SIZE)
				try:
					data_mc = mc.read_frame(num, verify_checksums=not args.ignore_checksum)
					if data_file != data_mc:
						raise MemcarduinoException("Mismatch:\nfile    = {}\nmemcard = {}".format(binascii.hexlify(data_file).decode(), binascii.hexlify(data_mc).decode()))
				except MemcarduinoException as e:
					sys.stdout.write("\rError in frame {}: {}\n".format(num, str(e)))
					ok = False
					break
			f.close()
			if ok:
				sys.stdout.write("\rDone! Card matches {}\n".format(args.verify))
				sys.stdout.flush()
			else:
				print("Error, abort")
				success = False

	except MemcarduinoException as e:
		print(e)
		print("Fatal error, exiting")
		success = False
	mc.close()

	if not success:
		sys.exit(1)
	else:
		sys.exit(0)
