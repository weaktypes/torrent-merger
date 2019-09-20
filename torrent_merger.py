import torrent_parser as tp
import hashlib
import os.path
import math
import re
from colorama import init, Fore, Back, Style
from collections import Counter

init()

def printRes(chunkNo, lineLen):
	
	if lineLen > 110:
		print("\n\n ", end="")
		lineLen = 0
	else:
		print(" ", end="")

	if checksumsResults[chunkNo] == 'M':
		print(f"{Back.GREEN}{Fore.BLACK} {chunkNo + 1} ", end="")
	elif checksumsResults[chunkNo] == 'H':
		print(f"{Back.YELLOW}{Fore.BLACK} {chunkNo + 1} ", end="")
	elif checksumsResults[chunkNo] == 'B':
		print(f"{Back.RED}{Fore.BLACK} {chunkNo + 1} ", end="")
	elif checksumsResults[chunkNo] == 'F':
		print(f"{Back.CYAN}{Fore.BLACK} {chunkNo + 1} ", end="")
	print(Style.RESET_ALL, end="")

	return lineLen + len(str(chunkNo + 1)) + 3

# print instructions
print("\nIncomplete Torrent Downloads Merger [1.0]")
print("=" * 41)
print("""\nThis program will take partially downloaded file ('main file') and try to fill in the missing pieces
from another partially downloaded file ('helper file'). The resulting file is saved into the same directory
with '[merged]' prefix. You can then put it in the place of the original file and do 'force recheck' in
the torrent client to acknowledge newly added pieces (or just keep the file if all the blank spaces
have been filled and it's 100% complete).""")

print("\nPrerequisites:")
print("""- torrent file used to download main file is required
  (use http://magnet2torrent.com to create one if you only have magnet link)
- the option to reserve space for the whole torrent must be selected in the torrent client,
  ie. the filesize of the file that is being downloaded must be set to the final size from the beginning
  (qBittorrent: Options => Downloads => Pre-allocate disk space for all files)
- the filesizes of main and helper file must match
- the directory containing the main file must be writable (the resulting file will be placed there)
- if the main file is a part of a multi-file torrent, additional files from the torrent are usually required
  to check the integrity of the first and/or last piece of the main file; the program will try to detect them
  in the same directory, so it's recommended to point to the main file in its original torrent download
  location where the other files from the torrent are stored (none of the existing files will be modified)\n""")

file01 = input("Path to partially downloaded main file:\n> ").replace('\\', '/').strip(' "')
file02 = input("Path to partially downloaded helper file:\n> ").replace('\\', '/').strip(' "')
torrentFile01 = input("Path to torrent file for main file:\n> ").replace('\\', '/').strip(' "')

# validate inputs
if not os.path.isfile(file01):
	exit(f"{Fore.RED}\nERROR: The path to main file is invalid{Style.RESET_ALL}")

if not os.path.isfile(file02):
	exit(f"{Fore.RED}\nERROR: The path to helper file is invalid{Style.RESET_ALL}")

if not os.path.isfile(torrentFile01):
	exit(f"{Fore.RED}\nERROR: The path to torrent file is invalid{Style.RESET_ALL}")

file01size = os.path.getsize(file01)
file02size = os.path.getsize(file02)
file01name = file01[file01.rfind('/') + 1:]
file02name = file02[file02.rfind('/') + 1:]
file01path = file01[:file01.rfind('/') + 1]
file02path = file02[:file02.rfind('/') + 1]

print(f"\nMain file....: {Fore.GREEN}{file01}{Style.RESET_ALL} | {Fore.YELLOW}{'{:,}'.format(file01size)} bytes{Style.RESET_ALL}")
print(f"Helper file..: {Fore.GREEN}{file02}{Style.RESET_ALL} | {Fore.YELLOW}{'{:,}'.format(file02size)} bytes{Style.RESET_ALL}")
print(f"Torrent......: {Fore.GREEN}{torrentFile01}{Style.RESET_ALL}")

try:
	torrentParsed = tp.parse_torrent_file(torrentFile01)
except:
	exit(f"{Fore.RED}\nERROR: Torrent file seems to be invalid{Style.RESET_ALL}")

if file01size != file02size:
	exit(f"{Fore.RED}\nERROR: The filesizes of main file and helper file don't match{Style.RESET_ALL}")

chunkSize = torrentParsed['info']['piece length']
checksums = torrentParsed['info']['pieces']
needPrevious = False
needNext = False

# select file if there are more in torrent
if 'files' in torrentParsed['info']:

	filesInTorrent = len(torrentParsed['info']['files'])

	print(f"\nThe torrent contains multiple files. Select the one that points to the main file [1-{filesInTorrent}]:\n")

	for i, fileEntry in enumerate(torrentParsed['info']['files']):
		if fileEntry['length'] == file01size and file01name == fileEntry['path'][-1]:
			print(f"{i + 1}: {Fore.GREEN}{'/'.join(fileEntry['path'])}{Style.RESET_ALL} | {Fore.YELLOW}{'{:,}'.format(fileEntry['length'])} bytes{Style.RESET_ALL}")
		else:
			print(f"{i + 1}: {'/'.join(fileEntry['path'])} | {'{:,}'.format(fileEntry['length'])} bytes")

	fileNoInTorrent = input("\n> ")

	while not re.match(r'^[0-9]+$', fileNoInTorrent) or int(fileNoInTorrent) > len(torrentParsed['info']['files']) or int(fileNoInTorrent) < 1:
		fileNoInTorrent = input("\nInvalid input, try again...\n\n> ")

	fileNoInTorrent = int(fileNoInTorrent) - 1

	sizeInTorrent = torrentParsed['info']['files'][fileNoInTorrent]['length']

	if sizeInTorrent != file01size:
		exit(f"{Fore.RED}\nERROR: Filesize of the selected file must match the filesize of the main file{Style.RESET_ALL}")

	# calculate offset
	if fileNoInTorrent != 0:
		totalOffset = 0
		for sizeTemp in torrentParsed['info']['files'][0:fileNoInTorrent]:
			totalOffset += sizeTemp['length']
		file01offset = chunkSize - (totalOffset % chunkSize)

		# we need previous file if chunk doesn't begin at start of main file
		if file01offset != 0:
			needPrevious = True
		
		# get rid of preceding checksums
		checksums = checksums[math.floor(totalOffset / chunkSize):]
	else:
		file01offset = 0

	# get rid of following checksums
	if fileNoInTorrent + 1 < len(torrentParsed['info']['files']):
		
		# we need next file if chunk doesn't end at end of main file
		file01overlap = chunkSize - ((sizeInTorrent - file01offset) % chunkSize)

		if file01overlap != 0:
			needNext = True

		neededChunksCount = math.ceil((sizeInTorrent - file01offset) / chunkSize)

		if file01offset > 0:
			neededChunksCount += 1
		if len(checksums) > neededChunksCount:
			checksums = checksums[0:neededChunksCount]

else:
	sizeInTorrent = torrentParsed['info']['length']
	print(f"\nFile in torrent.............: {Fore.GREEN}{torrentParsed['info']['name']}{Style.RESET_ALL} | {Fore.YELLOW}{'{:,}'.format(sizeInTorrent)} bytes{Style.RESET_ALL}")
	file01offset = 0

# find out which additional files are needed
additionalFiles = {}

if needPrevious == True:

	stillNeedBytes = (chunkSize - file01offset)
	currFile = fileNoInTorrent

	while stillNeedBytes > 0:
		currFile -= 1
		additionalFiles[currFile] = {'fullpath': '/'.join(torrentParsed['info']['files'][currFile]['path']), 'filename': torrentParsed['info']['files'][currFile]['path'][-1], 'size': torrentParsed['info']['files'][currFile]['length'], 'pos': currFile}
		stillNeedBytes -= torrentParsed['info']['files'][currFile]['length']

if needNext == True:

	stillNeedBytes = file01overlap
	currFile = fileNoInTorrent

	while stillNeedBytes > 0:
		currFile += 1
		try:
			additionalFiles[currFile] = {'fullpath': '/'.join(torrentParsed['info']['files'][currFile]['path']), 'filename': torrentParsed['info']['files'][currFile]['path'][-1], 'size': torrentParsed['info']['files'][currFile]['length'], 'pos': currFile}
			stillNeedBytes -= torrentParsed['info']['files'][currFile]['length']
		except:
			break

if len(additionalFiles) > 0:

	# check if the additional files are available
	gotAllRequired = True
	for i in additionalFiles:
		if os.path.exists(file01path + additionalFiles[i]['fullpath']) and os.path.getsize(file01path + additionalFiles[i]['fullpath']) == additionalFiles[i]['size']:
			additionalFiles[i]['available'] = file01path + additionalFiles[i]['fullpath']
		elif os.path.exists(file01path + additionalFiles[i]['filename']) and os.path.getsize(file01path + additionalFiles[i]['filename']) == additionalFiles[i]['size']:
			additionalFiles[i]['available'] = file01path + additionalFiles[i]['filename']
		else:
			additionalFiles[i]['available'] = False
			gotAllRequired = False

	if gotAllRequired == False:

		print("\nTo correctly calculate checksum of first and last chunk, the following file(s) need to be placed in the same")
		print("directory as the main file. If the file(s) are placed within directory structure in the torrent, you can")
		print("optionally place them in the same directory structure (relative to the main file). This step can be skipped,")
		print("but without these files, the checksum of first and/or last chunk of the main file cannot be verified.\n")

		for i in additionalFiles:
			if additionalFiles[i]['available'] == False:
				print(f"{Fore.GREEN}{additionalFiles[i]['fullpath']}{Style.RESET_ALL} | {Fore.YELLOW}{'{:,}'.format(additionalFiles[i]['size'])} bytes{Style.RESET_ALL}")

		input("\nPress Enter to continue...")

# check if the additional files were made available
if len(additionalFiles) > 0:

	for i in additionalFiles:
		if os.path.exists(file01path + additionalFiles[i]['fullpath']) and os.path.getsize(file01path + additionalFiles[i]['fullpath']) == additionalFiles[i]['size']:
			additionalFiles[i]['available'] = file01path + additionalFiles[i]['fullpath']
		elif os.path.exists(file01path + additionalFiles[i]['filename']) and os.path.getsize(file01path + additionalFiles[i]['filename']) == additionalFiles[i]['size']:
			additionalFiles[i]['available'] = file01path + additionalFiles[i]['filename']
		else:
			additionalFiles[i]['available'] = False

# get prev bytes if needed
if needPrevious == True:

	prevBytes = b''
	stillNeedBytes = chunkSize - file01offset
	pos = fileNoInTorrent - 1

	while stillNeedBytes > 0 and pos in additionalFiles:
		
		if additionalFiles[pos]['available'] == False:
			prevBytes = False
			break

		with open(additionalFiles[pos]['available'], 'rb') as f:
			currFilesize = os.path.getsize(additionalFiles[pos]['available'])
			
			# reading whole file
			if currFilesize <= stillNeedBytes:
				prevBytes = f.read() + prevBytes
				stillNeedBytes -= currFilesize
			else: # reading only part of file
				f.seek(currFilesize - stillNeedBytes)
				prevBytes = f.read() + prevBytes
				stillNeedBytes = 0

		pos -= 1

	# assert prevBytes == False or len(prevBytes) == chunkSize - file01offset

# get next bytes if needed
if needNext == True:

	nextBytes = b''
	stillNeedBytes = file01overlap
	pos = fileNoInTorrent + 1

	while stillNeedBytes > 0 and pos in additionalFiles and pos < filesInTorrent:
		
		if additionalFiles[pos]['available'] == False:
			nextBytes = False
			break

		with open(additionalFiles[pos]['available'], 'rb') as f:
			currFilesize = os.path.getsize(additionalFiles[pos]['available'])
			
			# reading whole file
			if currFilesize <= stillNeedBytes:
				nextBytes += f.read()
				stillNeedBytes -= currFilesize
			else: # reading only part of file
				nextBytes += f.read(stillNeedBytes)
				stillNeedBytes = 0

		pos += 1

# output current state of things
print(f"\nChunk size..................: {Fore.YELLOW}{chunkSize}{Style.RESET_ALL}")
print(f"Main file offset............: {Fore.YELLOW}{file01offset}{Style.RESET_ALL}")

if needPrevious == True:
	print(f"Need bytes from prev file(s): {Fore.YELLOW}{chunkSize - file01offset}{Style.RESET_ALL}")

if needNext == True:
	print(f"Need bytes from next file(s): {Fore.YELLOW}{file01overlap}{Style.RESET_ALL}")

if needPrevious == True or needNext == True:
	
	for i in additionalFiles:

		if additionalFiles[i]['available'] == False:
			print(f"{Fore.RED}Prev/next file not available: {additionalFiles[i]['fullpath']}{Style.RESET_ALL}")
		else:
			print(f"Prev/next file available....: {Fore.GREEN}{additionalFiles[i]['fullpath']} ({additionalFiles[i]['available']}){Style.RESET_ALL}")

if needPrevious == True:
	if prevBytes == False:
		print(f"{Fore.RED}Previous bytes grabbed......: N/A (one or more files are missing){Style.RESET_ALL}")
	else:
		print(f"Previous bytes grabbed......: {Fore.YELLOW}{len(prevBytes)}{Style.RESET_ALL}")

if needNext == True:
	if nextBytes == False:
		print(f"{Fore.RED}Next bytes grabbed..........: N/A (one or more files are missing){Style.RESET_ALL}")
	else:
		print(f"Next bytes grabbed..........: {Fore.YELLOW}{len(nextBytes)}{Style.RESET_ALL} (not necessarily an error if it differs from needed bytes)")

print("\n" + "=" * 113)
print(f"\nChunks ({Back.GREEN}{Fore.BLACK} X {Style.RESET_ALL} = working from main file, {Back.YELLOW}{Fore.BLACK} X {Style.RESET_ALL} = working from helper file, {Back.RED}{Fore.BLACK} X {Style.RESET_ALL} = not working, {Back.CYAN}{Fore.BLACK} X {Style.RESET_ALL} = unable to verify):\n")

# start combining the files
try:
	f1 = open(file01, 'rb')
	f2 = open(file02, 'rb')
except:
	exit(f"{Fore.RED}ERROR: Unable to open main or helper file")

try:
	fout = open(file01path + '[merged] ' + file01name, 'wb')
except:
	exit(f"{Fore.RED}ERROR: Unable to write to destination location ({file01path}[merged] {file01name})")

# M = working from main file, H = working from helper file, B = not working, F = unable to verify due to missing files
checksumsResults = []

posInFile = 0
posInChecksums = 0
resultLineLen = 0

# first chunk shenanigans
if needPrevious == True and prevBytes != False:
	# assert len(prevBytes) + file01offset == chunkSize

	bufferMain = f1.read(file01offset)
	bufferHelper = f2.read(file01offset)

	if hashlib.sha1(prevBytes + bufferMain).hexdigest() == checksums[posInChecksums]:
		checksumsResults.append('M')
		fout.write(bufferMain)
	elif hashlib.sha1(prevBytes + bufferHelper).hexdigest() == checksums[posInChecksums]:
		checksumsResults.append('H')
		fout.write(bufferHelper)
	else:
		checksumsResults.append('B')
		fout.write(bufferMain)

	posInFile = file01offset

elif needPrevious == True and prevBytes == False:
	checksumsResults.append('F')
	fout.write(f1.read(file01offset))
	posInFile = file01offset
else:
	bufferMain = f1.read(chunkSize)
	bufferHelper = f2.read(chunkSize)

	if hashlib.sha1(bufferMain).hexdigest() == checksums[posInChecksums]:
		checksumsResults.append('M')
		fout.write(bufferMain)
	elif hashlib.sha1(bufferHelper).hexdigest() == checksums[posInChecksums]:
		checksumsResults.append('H')
		fout.write(bufferHelper)
	else:
		checksumsResults.append('B')
		fout.write(bufferMain)
	posInFile = chunkSize

resultLineLen = printRes(posInChecksums, resultLineLen)

posInChecksums += 1

# next chunks
while posInFile < file01size and (needNext == False or posInFile + chunkSize < file01size):

	f1.seek(posInFile)
	f2.seek(posInFile)

	bufferMain = f1.read(chunkSize)

	if hashlib.sha1(bufferMain).hexdigest() == checksums[posInChecksums]:
		checksumsResults.append('M')
		fout.write(bufferMain)
	else:
		bufferHelper = f2.read(chunkSize)
		if hashlib.sha1(bufferHelper).hexdigest() == checksums[posInChecksums]:
			checksumsResults.append('H')
			fout.write(bufferHelper)
		else:
			checksumsResults.append('B')
			fout.write(bufferMain)

	resultLineLen = printRes(posInChecksums, resultLineLen)

	posInFile += chunkSize
	posInChecksums += 1

# overlapping chunk shenanigans
if needNext == True:

	f2.seek(f1.tell()) # set helper file pointer to same position as main file pointer

	bufferMain = f1.read(chunkSize)
	bufferHelper = f2.read(chunkSize)

	if nextBytes == False:
		checksumsResults.append('F')
		fout.write(bufferMain)
	elif hashlib.sha1(bufferMain + nextBytes).hexdigest() == checksums[posInChecksums]:
		checksumsResults.append('M')
		fout.write(bufferMain)
	elif hashlib.sha1(bufferHelper + nextBytes).hexdigest() == checksums[posInChecksums]:
		checksumsResults.append('H')
		fout.write(bufferHelper)
	else:
		checksumsResults.append('B')
		fout.write(bufferMain)

	resultLineLen = printRes(posInChecksums, resultLineLen)

print(Style.RESET_ALL)

f1.close()
f2.close()
fout.close()

counts = Counter(checksumsResults)

print("\n" + "=" * 113)
print("\nMerged file:\n")

print("Chunks used from main file..: " + (str(counts['M']) if 'M' in counts else "0"))
print("Chunks used from helper file: " + (str(counts['H']) if 'H' in counts else "0"))
print("Bad chunks remaining........: " + (str(counts['B']) if 'B' in counts else "0"))
print("Unverifiable chunks.........: " + (str(counts['F']) if 'F' in counts else "0"))

print(f"\nMerged file saved to: {Fore.GREEN}{file01path}[merged] {file01name}{Style.RESET_ALL}\n")

input("Press any key to exit...")
