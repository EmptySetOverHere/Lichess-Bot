import sys
import os
import subprocess
import threading
import re
import time
import shlex
from collections import deque
from io import StringIO

try:
	from PIL import Image, ImageDraw
except ImportError as ex:
	print(ex)
	exit()

class adb(threading.Thread):

	def __init__(self):
		os.system('cls')
		self.user_input = input('1:USB connection \n2:Tcp\\ip connection \nPlease choose a connection method: ')
		while self.user_input not in '12':
			self.user_input = input('Please enter the index (1 or 2): ')
		
		'''
		ADB remote connection will automatically establishd once instantiated
		'''

		if self.user_input == '1': # USB Connection
			self.process = subprocess.run(['adb', 'devices'], capture_output = True)
			self.output = self.process.stdout.decode('utf-8')
			print(self.output)
			if self.output.split()[-1] == 'device':
				print('Connection successfully established')
				print('Please do not detached your device')
			else:
				raise Exception('No device found')

		if self.user_input == '2':	#Tcp / ip listener
			self.ip_match = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}') #compile regular expression of ip address
			self.serial_number_match = re.compile(r'')
			self.connected = False
			try:
				self.process = subprocess.run(['adb', 'devices'], capture_output = True)
				self.output = self.process.stdout.decode('utf-8')
				self.connected = True if re.search(self.ip_match, self.output) != None else False
				#Check adb connection
				if self.output.find('unauthoried') == -1 and self.connected is not True:
					print('\nEstablishing Remote Connection ...')
					print('Please do not plug out your USB cable')
					try:
						self.process = subprocess.run(['adb', 'shell', 'ip', 'route'], capture_output = True)
						self.output = self.process.stdout.decode('utf-8')
						self.output = re.search(self.ip_match, self.output[-20:])
						self.process = subprocess.run(['adb', 'tcpip', '5555'], capture_output = True)

						if self.process.stderr.decode('utf-8') == '' and self.output != None:
							self.process = subprocess.run(['adb', 'connect', self.output.group(0)], capture_output = True)
							self.output = self.process.stdout.decode('utf-8')
							print(self.output)
							if len(self.output) > 50: #To avoid output error
								raise Exception
						else:
							raise Exception

					except Exception as ex:
						print(ex)
						print('Connection Fails')
						print('Please check if your mobile device is attached')
						print('Please check if developer mode is swiched on')
						exit()

				elif self.connected is not True:
					print('\nPlease make sure the device has been grant debugging authorisations: ')
					print('-->\tsetting')
					print('-->\tDeveloper options')
					print('-->\tUSB debugging')
					print('-->\tRevoke USB debugging authorisations')
					print('Restart bash/command prompt')
					exit()

			except Exception as ex:
				print(ex)
				exit()

			os.system('adb devices')
			print('Connection successfully established')
			print('You are now allowed to plug out your USB cable\n')
			self.user_input = input('Have you detached your device? [Y/N]: ')
			if self.user_input.lower() != 'y':
				print('To ensure a successful run of this program\nPlease follow the instrutions given')
				exit()
	
		self.connected = True

	def execute(self, cmd):
		#print('adb running command: {}'.format(cmd))
		self.command = shlex.split(cmd)
		self.command.insert(0 , 'adb')
		self.process = subprocess.run(self.command, capture_output = True)
		self.output, self.error = self.process.stdout, self.process.stderr
		if self.error.decode('utf-8') != '':
			print(self.error)
			raise Exception('Error code is detected when running the command:\n{}'.format(self.command))
		return self.output

	def run(self):
		#Keep Tracking the connection
		while self.connected:
			self.process = subprocess.run(['adb', 'devices'], capture_output = True)
			self.output = self.process.stdout.decode('utf-8')
			self.connected = True if re.search(self.ip_match, self.output) != None else False
			time.sleep(2)


class Screenshot():
	SCREENSHOT_WAY = 3

	def __init__(self, img_name, adb_instance):
		super().__init__()
		try:
			self.adb = adb_instance
			self.img_name = "Test.png"
			self.image_queque = deque()
			if not os.path.isdir('Image'):
				os.mkdir('Image')
		except Exception as ex:
			print(ex)
			exit()

		"""
		Alter to a specific method suitable to take screenshots on current device
		"""
		while True:
			if os.path.isfile('Test.png'):
				try:
					os.remove('Test.png')
				except Exception:
					pass
			if Screenshot.SCREENSHOT_WAY < 0:
				print('Current device is not supported')
				sys.exit()
			try:
				im = self.pull_screenshot()
				im.load()
				im.close()
				print('Adopting method {} for screen-capture...'.format(Screenshot.SCREENSHOT_WAY))
				break
			except Exception as ex:
				Screenshot.SCREENSHOT_WAY -= 1

		self.img_name = img_name
		if self.img_name.split()[0] != self.img_name:
			raise Exception('Image name should not contain any spaces')
			exit()
		self.image_taken = None


	def pull_screenshot(self):
		'''
		Adopting 4 different method to capture screen
		'''
		if len(self.image_queque) >= 5:
			self.image_queque.popleft()

		if 1 <= Screenshot.SCREENSHOT_WAY <= 3:
			process = subprocess.run(['adb','shell screencap', '/sdcard/{}'.format(self.img_name)], capture_output = True)
			binary_screenshot = process.stdout
			if Screenshot.SCREENSHOT_WAY == 2:
				binary_screenshot = binary_screenshot.replace(b'\r\n', b'\n')
			elif Screenshot.SCREENSHOT_WAY == 1:
				binary_screenshot = binary_screenshot.replace(b'\r\r\n', b'\n')
				self.image_taken = Image.open(StringIO(binary_screenshot))
				self.image_queque.append(self.image_taken)
				return self.image_taken

		elif Screenshot.SCREENSHOT_WAY == 0:
			os.chdir('Image')
			self.adb.execute('shell screencap /sdcard/{}'.format(self.img_name))
			self.adb.execute('pull /sdcard/{}'.format(self.img_name))
			self.image_taken = Image.open('./{}'.format(self.img_name))
			self.image_queque.append(self.image_taken)
			os.chdir('..')
			return self.image_taken

class stopwatch(threading.Thread):

	def __init__(self):
		super().__init__()
		self.game_duration = 0
		self.reference = 0
		self.markpoint = 0
		self.stopped = False

	def run(self):
		self.reference = time.time()
		while not self.stopped:
			self.markpoint = time.time()
			self.game_duration = int(abs(self.reference - self.markpoint) + 0.5)
			print(self.game_duration)
			time.sleep(1)

	def stop(self):
		self.stopped = True

	def go(self):
		self.stopped = False

	def reset(self):
		self.reference = time.time()
		self.game_duration = 0
		self.stopped = False
		


if __name__ == '__main__':
	stopwatch = stopwatch()
	stopwatch.start()
	while stopwatch.game_duration < 200:
		time.sleep(2)

	stopwatch.stop()
	print(stopwatch.is_alive())
	stopwatch.reset()
	while stopwatch.game_duration < 10:
		time.sleep(2)