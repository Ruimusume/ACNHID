
#from Msbt import MsbtFile
class MsbtFile(object):

	def __init__(self, path, clean=True):
		#print(path)
		self.path = path
		self.data = list()
		with open(path, mode='rb') as file:
			self.data = file.read()

		if self.read_position(0, 8) != b'MsgStdBn':
			print('Invalid signature of file {}!'.format(path))
			return
		
		pointer = 0x20
		def read_pointer(length):
			nonlocal pointer
			p_data = self.read_position(pointer, length)
			pointer += length
			return p_data
		
		# reading sections
		self.lbl1_labels = list()
		self.txt2_strings = list()
		for _ in range(self.get_section_count()):
			pos = pointer
			try:
				while self.data[pointer] == b'\xab'[0]:
					pointer += 1
				signature = read_pointer(4)
				signature = signature.decode('utf-8')
			except:
				#print(signature)
				signature = 'UNK1'
			
			section_size = int.from_bytes(read_pointer(4), 'little')
			#print('Signature: {}'.format(signature))
			#print('signature in file {}:{:08X} {}'.format(path, pos, signature))

			if signature == 'LBL1': # label
				read_pointer(8) # padding
				lbl1_pos = pointer
				entry_count = int.from_bytes(read_pointer(4), 'little')
				#print('\tLBL1 has {} entries [{:08X}]'.format(entry_count, pointer))
				groups = list()
				for entry in range(entry_count):
					groups.append((int.from_bytes(read_pointer(4), 'little'), int.from_bytes(read_pointer(4), 'little')))
					# number of labels, offset
				
				for num_labels, offset in groups:
					group_labels = list()
					pointer = lbl1_pos + offset
					#print('\tGroup#{} has {} labels [{:08X}]'.format(group_num, num_labels, pointer))
					for _ in range(num_labels):
						length = int.from_bytes(read_pointer(1), 'little')
						name = read_pointer(length)
						#print(name)
						index = int.from_bytes(read_pointer(4), 'little')
						group_labels.append((index, name))


					self.lbl1_labels.append(group_labels)
				#print(pointer, lbl1_pos + section_size)

			elif signature == 'TXT2': # text
				read_pointer(8) # padding
				txt2_pos = pointer
				entry_count = int.from_bytes(read_pointer(4), 'little')
				offsets = [int.from_bytes(read_pointer(4), 'little') for _ in range(entry_count)]
				for entry in range(entry_count):
					startPos = offsets[entry] + txt2_pos
					endPos = txt2_pos + offsets[entry+1] if entry + 1 < entry_count else txt2_pos + section_size
					length = endPos - startPos
					self.txt2_strings.append(self.read_position(startPos, length)) # add decoding!! .decode(self.get_encoding_name())
				
				# seek to end of section
				pointer = txt2_pos + section_size

			#elif signature in ['NLI1', 'ATR1', 'ATO1', 'TSY1']:
			#	print('signature in file {}:{} {}'.format(path, pos, signature))
			else:
				read_pointer(8) # padding
				read_pointer(section_size) # skip over it
				#print('{:08X}'.format(pointer))
		
		#print('Processing lbl1')
		self.lbl1_labels_flat = list()
		for group in self.lbl1_labels:
			for item in group:
				item = (item[0], item[1].decode('utf-8'))
				self.lbl1_labels_flat.append(item)
		self.lbl1_labels_flat.sort(key=lambda x: x[0])
		
		#print('Processing txt2', len(self.txt2_strings))
		self.txt2_strings_decoded = list()
		
		for txt2_string in self.txt2_strings:
			if txt2_string[0:4] == b'\x0e\x002\x00':
				i = 0
				while i < len(txt2_string) and txt2_string[i] != b'\xcd'[0]:
					i += 1
				i += 1
				if i < len(txt2_string):
					txt2_string = txt2_string[i:]

			txt2_string = txt2_string[:-2]
			try:
				s = txt2_string.decode(self.get_encoding_name())
				s = s.replace('\x0en\x1e\x00', '<N>')
				self.txt2_strings_decoded.append(s)
				#print(s)
			except KeyboardInterrupt:
				exit()
			except:
				print(txt2_string, 'Exception')




	# other stuff

	def read_position(self, position, length):
		return self.data[position:(position+length)]
	
	def get_byte_order_mark(self):
		return self.read_position(0x8, 2)
	
	def get_encoding(self):
		return int.from_bytes(self.read_position(0xC, 1), 'little')
	
	def get_encoding_name(self):
		encoding = self.get_encoding()
		if encoding == 0:
			return 'utf-8'
		elif encoding == 1:
			return 'utf-16le'
		elif encoding == 2:
			return 'utf-16be'
	
	def get_version(self):
		return int.from_bytes(self.read_position(0xD, 1), 'little')
	
	def get_section_count(self):
		return int.from_bytes(self.read_position(0xE, 2), 'little')
	
	def get_filesize(self):
		return int.from_bytes(self.read_position(0x10, 4), 'little')


if __name__ == "__main__":
	import os
	# normal item ids
	base_path = os.path.join(*'romfs_unpacked/Message/String_EUen'.split('/'))
	load_msbt = lambda path: (lambda _path: [MsbtFile(os.path.join(_path, msbt)) for msbt in os.listdir(_path)])(os.path.join(*path.split('/')))
	msbt_files = load_msbt(os.path.join(base_path, 'item'))
	
	# load clothing. 
	outfitName = load_msbt(os.path.join(base_path, 'Outfit/GroupName'))
	outfitColor = load_msbt(os.path.join(base_path, 'Outfit/GroupColor'))
	#print(len(outfitName))
	# create a small dictionary of <int, str> of the group names
	outfitNameMapping = dict()
	# (Type, type_Id) -> GroupName
	
	outfits = dict()
	# (type, Id) -> (GroupName, Color)
	for msbt in outfitName:
		outfitType = msbt.path.split('_')[-1].split('.')[0]
		for label, (_, item_label) in zip(msbt.txt2_strings_decoded, msbt.lbl1_labels_flat):
			outfitNameMapping[(outfitType, int(item_label))] = label
	
	for msbt in outfitColor:
		outfitType = msbt.path.split('_')[-1].split('.')[0]
		outfits[outfitType] = dict()
		for label, (_, item_label) in zip(msbt.txt2_strings_decoded, msbt.lbl1_labels_flat):
			group_id, _, item_id = item_label.split('_')
			group_id = int(group_id)
			item_id = int(item_id)
			outfits[outfitType][item_id] = (outfitNameMapping[(outfitType, group_id)], label)

	# Name, Internal name, Id? sure
	with open('item_ids.txt', 'w', encoding='utf-16') as file:
		for msbt in msbt_files:
			file.write('{}\n'.format(msbt.path))
			for item_name, (_, item_label) in zip(msbt.txt2_strings_decoded, msbt.lbl1_labels_flat):
				# get item id
				item_id = item_label.split('_')[-1]
				if item_id == 'pl':
					continue
				item_id = int(item_id)
				try:
					file.write('{}, {} [{}]\n'.format(item_name, hex(item_id)[2:], item_label))
				except:
					print(item_name, hex(item_id)[2:], item_label)
			file.write('\n')
		
		for outfitType, outfitDict in outfits.items():
			file.write('Outfits/{}\n'.format(outfitType))
			for item_id, (outfitName, outfitColor) in outfitDict.items():
				file.write('{}, {}, [{} | {}]\n'.format(outfitName, hex(item_id)[2:], outfitName, outfitColor))
			
			file.write('\n')