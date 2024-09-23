import os
import argparse
import struct
import json

parser = argparse.ArgumentParser(description="Converts .CIN files to more common and easily edited formats.")
parser.add_argument("input", metavar='file', type=str, help="The CIN to edit.")
parser.add_argument("type", choices=['json', 'cin'], type=str, help="The filetype that the input will be converted to.")
args = parser.parse_args()

def read_data(desType, byteData):
	return struct.unpack(desType, byteData)[0]
	
def get_cin_type(value):
	if isinstance(value, str):
		if value == "CIN_MASK": return 0
		if value == "CIN_SHAPE": return 1
		if value == "CIN_TEXTURE": return 2
		else: return int(value[4:], 16) # get number from "UNK_XX"
	elif isinstance(value, int):
		if value == 0: return "CIN_MASK"
		if value == 1: return "CIN_SHAPE"
		if value == 2: return "CIN_TEXTURE"
		else: return f'UNK_{value:02X}'
	
def read_chunk(byteSlice):
	return {
		"Type": get_cin_type(read_data('<b', byteSlice[0:1])),
		"Prop": read_data('<b', byteSlice[1:2]),
		"Colour": {
			"Red": read_data('<H', byteSlice[2:4]),
			"Green": read_data('<H', byteSlice[4:6]),
			"Blue": read_data('<H', byteSlice[6:8]),
			"Alpha": read_data('<H', byteSlice[8:0xA])
		},
		"StartX": read_data('<h', byteSlice[0xA:0xC]),
		"StartY": read_data('<h', byteSlice[0xC:0xE]),
		"EndX": read_data('<h', byteSlice[0xE:0x10]),
		"EndY": read_data('<h', byteSlice[0x10:0x12])
	}
		
def write_chunk(chunkDict):
	return struct.pack(
		'<bbHHHHhhhh',
		get_cin_type(chunkDict["Type"]),
		chunkDict["Prop"],
		chunkDict["Colour"]["Red"],
		chunkDict["Colour"]["Green"],
		chunkDict["Colour"]["Blue"],
		chunkDict["Colour"]["Alpha"],
		chunkDict["StartX"],
		chunkDict["StartY"],
		chunkDict["EndX"],
		chunkDict["EndY"]
	)

def cin_to_json(iBytes):
	dataPosition = 0x2A
	outJS = {
		"Header": {}
	}
	# testMagic = read_data('<I', iBytes[:4])
	if read_data('<I', iBytes[:4]) != 0x4E4943:
		outJS["Header"]["HoldFrame"] = read_data('<H', iBytes[:2])
		outJS["Header"]["ObjectCount"] = read_data('<H', iBytes[2:4])
		outJS["Header"]["u8_UnkColours"] = struct.unpack('<'+'B'*22, iBytes[4:0x1A])
		dataPosition -= 6
	else:
		outJS["Header"]["Magic"] = read_data('<4s', iBytes[:4]).decode('utf-8').rstrip('\x00')
		outJS["Header"]["u16_Unknown1"] = read_data('<H', iBytes[4:6])
		outJS["Header"]["HoldFrame"] = read_data('<H', iBytes[6:8])
		outJS["Header"]["ObjectCount"] = read_data('<H', iBytes[8:0xA])
		outJS["Header"]["u8_UnkColours"] = struct.unpack('<'+'B'*22, iBytes[0xA:0x20])
	# TODO: Read this & u8_UnkColours to hex array ala LEET
	outJS["u8_Unknown"] = struct.unpack('<'+'B'*10, iBytes[dataPosition-10:dataPosition])
	outJS["Objects"] = []
	for i in range(outJS["Header"]["ObjectCount"]):
		curObject = {}
		frame = 0
		while True:
			objEnd = read_data('<h', iBytes[dataPosition:dataPosition+2])
			if objEnd == (-512):
				# print("End of object!")
				curObject["EndChunk"] = read_chunk(iBytes[dataPosition:dataPosition+0x12])
				dataPosition += 0x12
				break
			curObject[f'Frame_{frame:02}'] = []
			while True:
				frameEnd = read_data('<h', iBytes[dataPosition:dataPosition+2])
				curObject[f'Frame_{frame:02}'].append(read_chunk(iBytes[dataPosition:dataPosition+0x12]))
				dataPosition += 0x12
				if frameEnd == (-256):
					# print("End of frame!")
					frame += 1
					break
		outJS["Objects"].append(curObject)
		# print(f'Object {i}, objEnd {objEnd}, dataPos {dataPosition}')
	with open(f'{args.input}.json', "w") as jsOut:
		json.dump(outJS, jsOut, indent = 2)
	print("Converted to JSON successfully!")
	
def json_to_cin(inJSON):
	outBytes = b''
	# Write header data + Write magic bytes if present
	if "Magic" in inJSON["Header"]:
		outBytes += struct.pack(
			'<4sH',
			inJSON["Header"]["Magic"].encode('utf-8'),
			inJSON["Header"]["u16_Unknown1"]
		)
	outBytes += struct.pack(
		'<HH',
		inJSON["Header"]["HoldFrame"],
		inJSON["Header"]["ObjectCount"]
	)
	outBytes += bytes(inJSON["Header"]["u8_UnkColours"]) + bytes(inJSON["u8_Unknown"])
	# Write objects
	for obj in inJSON["Objects"]:
		for listName, listValue in obj.items():
			if listName == "EndChunk":
				outBytes += write_chunk(listValue)
			else:
				for chunk in listValue:
					# print(chunk)
					outBytes += write_chunk(chunk)
	with open(f'{args.input}.cin', "wb") as outStream:
		outStream.write(outBytes)
	print("Converted to CIN successfully!")

def print_unsupported_type():
	print(f'{args.input} is not currently supported by script!')

def load_binary(path):
	with open(path, "rb") as inStream:
		return inStream.read(os.path.getsize(args.input))

def load_json(path):
	with open(path, "r") as jsonStream:
		return json.load(jsonStream)

if os.path.isfile(args.input):
	lowerInput = args.input.lower()
	if args.type == 'json':
		if lowerInput.endswith('.json'):
			print("Can't convert .json to .json! Stopping script!")
		elif lowerInput.endswith('.cin'):
			print(f'Converting {args.input} to JSON file...')
			cin_to_json(load_binary(args.input))
		else:
			print_unsupported_type()
	else:
		if lowerInput.endswith('.cin'):
			print("Can't convert .cin to .cin! Stopping script!")
		elif lowerInput.endswith('.json'):
			print(f'Converting {args.input} to CIN file...')
			json_to_cin(load_json(args.input))
		else:
			print_unsupported_type()
