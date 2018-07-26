'''
This is the main module which imports and drives all components to run
'''
import os
import sys
import json
import time
from collections import deque, OrderedDict

if sys.version_info.major != 3:
	
	print('Please setup python 3 on this device')
	exit()

try:
	import toolkit
	import chess, chess.uci
	from PIL import ImageDraw
	#initialize chess board
	chess_board = chess.Board()
	#import configuration file
	with open('config.json') as f:
		config = json.loads(f.read())
	#initialize adb connection
	adb = toolkit.adb()
	#Bridge connection between chess engine and python-chess interface
	chess_engine = chess.uci.popen_engine(config['engine_uci_path'])
	info_handler = chess.uci.InfoHandler()
	chess_engine.info_handlers.append(info_handler)
	#initalize screenshot module
	screencap1 = toolkit.Screenshot('Screencap_1.png', adb)
	screencap2 = toolkit.Screenshot('Screencap_2.png', adb)
	stopwatch = toolkit.stopwatch()

except Exception as ex:
	print(ex)
	exit()

def engine_make_move(board_info):
	# A simple encapsulated chess engine which make moves on the chess board
	def on_go_finish(command):
		bestmove, ponder = command.result()

	chess_engine.position(chess_board)
	chess_engine.go(movetime=500)
	try:
		engine_move = chess_engine.bestmove.uci()
		chess_board.push_uci(engine_move) # make movement on local chess board
	
		# Make actual movement on lichess
		touch_point_A = board_info[engine_move[:2]]
		touch_point_B = board_info[engine_move[-2:]]
		adb.execute('shell input tap {} {}'.format(touch_point_A[0], touch_point_A[1]))
		adb.execute('shell input tap {} {}'.format(touch_point_B[0], touch_point_B[1]))

	except:
		engine_move = None	

	os.system('cls')
	print('Engine\'s move ==> \t{}\n'.format(engine_move))
	print(chess_board)

def create_chess_board_nodes(im):
	#locate the chess board in pixel coordinate system
	#return piece color and board info
	w, h = im.size
	im_pixel = im.load()
	first_square = None
	square_width, square_height = 0, 0
	#Look for the pixel at the top left corner of the chess board
	for x in range(0, 5):
		for y in range(h//4, 3*h//4):
			next_pixel_color = im_pixel[x, y+1]
			current_pixel_color = im_pixel[x, y]
			if ((next_pixel_color[0] + 10 < current_pixel_color[0] or next_pixel_color[0] -10 > current_pixel_color[0]) and
				(next_pixel_color[1] + 10 < current_pixel_color[1] or next_pixel_color[1] -10 > current_pixel_color[1]) and
				(next_pixel_color[2] + 10 < current_pixel_color[2] or next_pixel_color[2] -10 > current_pixel_color[2])):
				first_square = (x + 1, y + 1) # plus one to ensure scaned pointed landed correctly in the first squre
				break
		if first_square is not None:
			break

	if first_square is None or im_pixel[first_square[0], first_square[1]][0] < 200:
		# fails to mark the top left corner 
		print('Unable to locate chess board')
		return None, None

	#look for square width and square_height
	for x in range(first_square[0], 400):
		next_pixel_color = im_pixel[x+1, first_square[1]]
		current_pixel_color = im_pixel[x, first_square[1]]
		if ((next_pixel_color[0] + 10 < current_pixel_color[0] or next_pixel_color[0] -10 > current_pixel_color[0]) and
			(next_pixel_color[1] + 10 < current_pixel_color[1] or next_pixel_color[1] -10 > current_pixel_color[1]) and
			(next_pixel_color[2] + 10 < current_pixel_color[2] or next_pixel_color[2] -10 > current_pixel_color[2])):
			square_width = x - first_square[0]
			break

	for y in range(first_square[1], first_square[1] + 400):
		next_pixel_color = im_pixel[first_square[0], y+1]
		current_pixel_color = im_pixel[first_square[0], y]
		if ((next_pixel_color[0] + 10 < current_pixel_color[0] or next_pixel_color[0] -10 > current_pixel_color[0]) and
			(next_pixel_color[1] + 10 < current_pixel_color[1] or next_pixel_color[1] -10 > current_pixel_color[1]) and
			(next_pixel_color[2] + 10 < current_pixel_color[2] or next_pixel_color[2] -10 > current_pixel_color[2])):
			square_height = y - first_square[1]
			break

	if (square_width < w//8 - 100 or square_height > w//8 + 100) or (square_height < w//8 -100 or square_height > w//8 + 100):
		# Irregular square height and width detection
		print('Unable to locate chess board')
		return None, None

	#Determine the piece color the engine is going to use
	first_square_color = im_pixel[square_width//2 + first_square[0], square_height//2 + first_square[1]]
	if  first_square_color[0] > 240 and first_square_color[1] > 230 and first_square_color[2] > 230:
		uci_coordinates = [chr(x) + str(num) for num in range(1, 9) for x in reversed(range(97, 105))]
		print('Piece color: \tBlack')
		Piece_color = 'Black'
	elif first_square_color[0] < 40 and first_square_color[1] < 40 and first_square_color[2] < 50:
		uci_coordinates = [chr(x) + str(num) for num in reversed(range(1, 9)) for x in range(97, 105)]
		print('Piece color: \tWhite')
		Piece_color = 'White'
	else:
		print('Unable to locate chess board')
		return None, None

	board_info = [(x, y) for y in range(first_square[1] + square_height//2, first_square[1] + 8*square_height, square_height)
						 for x in range(first_square[0] + square_width//2, first_square[0] + 8*square_width, square_width)]

	board_info = OrderedDict(zip(uci_coordinates, board_info))
	return board_info, Piece_color

def opponent_make_move(first_image, second_image, board_info, Piece_color):
	#dedicated to look for what move opponent has been made
	def validity_test(opponent_move_uci):
		for test_times in range(2):
			# test two times
			opponent_move_uci = opponent_move_uci[-2:] + opponent_move_uci[:2]
			try:
				chess_board.push_uci(opponent_move_uci)
				os.system('cls')
				print('Opponent\'s move ==> \t{}\n'.format(opponent_move_uci))
				print(chess_board)
				return True
			except:
				pass

	first_image_pixel = first_image.load()
	second_image_pixel = second_image.load()
	opponent_move_uci = ''
	oppnent_piece_color = 'Black' if Piece_color == 'White' else 'White'

	if chess_board.has_castling_rights(oppnent_piece_color):
		#check castling
		for index, key in enumerate(board_info):
			if (((index == 2 or index == 4 or index == 6) and oppnent_piece_color == 'Black') or 
			   (((index == 1 or index == 3 or index == 5) and oppnent_piece_color == 'White'))):
				pos = board_info[key]
				first_image_color = first_image_pixel[pos[0], pos[1]]
				second_image_color = second_image_pixel[pos[0], pos[1]]

				if abs(first_image_color[0] - second_image_color[1]) > 50:
					opponent_move_uci += key
				
				if len(opponent_move_uci) == 4:
					break

		if validity_test(opponent_move_uci) == True:
			return True

	#color comparison for the two images taken at different timing
	for uci, pos in board_info.items():
			
		first_image_color = first_image_pixel[pos[0], pos[1]]
		second_image_color = second_image_pixel[pos[0], pos[1]]

		if abs(first_image_color[0] - second_image_color[1]) > 50:
			opponent_move_uci += uci
		
		if len(opponent_move_uci) == 4:
			break


	if validity_test(opponent_move_uci) == True:
		return True

	#color density test
	if len(opponent_move_uci) != 0:
		opponent_move_uci = ''
		color_density = 0.7 * 40 * 40

		for uci, pos in board_info.items():
			changed_pixel = 0

			for x in range(0, 40):
				for y in range(0, 40):
					first_image_color = first_image_pixel[pos[0] - 40 + x, pos[1] - 40 + y]
					second_image_color = second_image_pixel[pos[0] - 40 + x, pos[1] - 40 + y]

					if abs(first_image_color[0] - second_image_color[1]) > 50:
						changed_pixel += 1

			if changed_pixel > color_density:
				opponent_move_uci += uci

			if len(opponent_move_uci) == 4:
				break

	if validity_test(opponent_move_uci) == True:
		return True

	#Green Color detection
	opponent_move_uci = ''
	for uci, pos in board_info.items():

		for x in range(0, 40):
			for y in range(0, 40):
				second_image_color = second_image_pixel[pos[0] - x, pos[1] - y]
				if ((second_image_color[0] > 165 and second_image_color[0] < 175) and
					(second_image_color[1] > 160 and second_image_color[1] < 165) and 
					(second_image_color[2] > 55 and second_image_color[2] < 65)):
					opponent_move_uci += uci

				elif ((second_image_color[0] > 200 and second_image_color[0] < 210) and
					  (second_image_color[1] > 205 and second_image_color[1] < 215) and 
					  (second_image_color[2] > 100 and second_image_color[2] < 115)):
					opponent_move_uci += uci
				
		if len(opponent_move_uci) == 4:
			break
	
	
	if validity_test(opponent_move_uci) == True:
		return True

	return False

def find_opponent():
	# look for the postion of the rematch button
	im = screencap1.pull_screenshot()
	w, h = im.size
	im_pixel = im.load()
	widget_pos = None
	widget_height, widget_width = None, None
	widget_found = False
	first_pixel, second_pixel = None, None

	for y in range(150, 300):
		for x in range(w-300, w-1):
			current_pixel_color = im_pixel[x, y]
			next_pixel_color = im_pixel[x + 1, y]

			if ((next_pixel_color[0] + 10 < current_pixel_color[0] or next_pixel_color[0] -10 > current_pixel_color[0]) and
			    (next_pixel_color[1] + 10 < current_pixel_color[1] or next_pixel_color[1] -10 > current_pixel_color[1]) and
			    (next_pixel_color[2] + 10 < current_pixel_color[2] or next_pixel_color[2] -10 > current_pixel_color[2])):
				widget_pos = (x, y)
				widget_found = True
				break
		
		if widget_found:
			break

	if widget_found:
		adb.execute('shell input tap {} {}'.format(widget_pos[0] + 30, widget_pos[1] + 30))
		widget_pos = None
		widget_found = False
		time.sleep(0.5)
		im = screencap1.pull_screenshot()
		w, h = im.size
		im_pixel = im.load()
	else:
		print('Unable to locate the widget')
		return False

	for y in range(0, h//5, 2):
		first_pixel, second_pixel = None, None
		for x in range(0, w - 1, 2):
			current_pixel_color = im_pixel[x, y]
			next_pixel_color = im_pixel[x + 1, y]

			if current_pixel_color[0] > 240 and current_pixel_color[1] > 240 and current_pixel_color[2] > 240 and first_pixel == None:
				first_pixel = (x + 1, y)

			if ((next_pixel_color[0] + 10 < current_pixel_color[0] or next_pixel_color[0] -10 > current_pixel_color[0]) and
				(next_pixel_color[1] + 10 < current_pixel_color[1] or next_pixel_color[1] -10 > current_pixel_color[1]) and
				(next_pixel_color[2] + 10 < current_pixel_color[2] or next_pixel_color[2] -10 > current_pixel_color[2])) and first_pixel != None:
				second_pixel = (x, y)

			if first_pixel != None and second_pixel != None and (second_pixel[0] - first_pixel[0]) > w*0.8:
				widget_pos = first_pixel
				widget_found = True
				widget_width = abs(second_pixel[0] - first_pixel[0])
				break
		
		if widget_found:
			break
	

	if widget_found:
		for y in range(widget_pos[1] + 10, h):
			current_pixel_color = im_pixel[widget_pos[0] + 5, y]
			next_pixel_color = im_pixel[widget_pos[0] + 5, y + 1]
			if ((next_pixel_color[0] + 10 < current_pixel_color[0] or next_pixel_color[0] -10 > current_pixel_color[0]) and
			    (next_pixel_color[1] + 10 < current_pixel_color[1] or next_pixel_color[1] -10 > current_pixel_color[1]) and
			    (next_pixel_color[2] + 10 < current_pixel_color[2] or next_pixel_color[2] -10 > current_pixel_color[2])):
				widget_height = abs(y - widget_pos[1])
				break
		
		if widget_height != None and widget_height > h//3:
			adb.execute('shell input tap {} {}'.format(widget_pos[0] + widget_width//2, widget_pos[1] + widget_height//2))
			return True
		
		else:
			print('Unable to locate the widget')
			return False
	
	print('Unable to locate the widget')
	return False

def abortion_or_resignation(im):
	#response to game abortion or opponent's resignation
	w, h = im.size
	im_pixel = im.load()

	for y in range(h//2, h//2 + 200, 2):
		first_pixel , second_pixel = None, None
		for x in range(0, w - 1):
			current_pixel_color = im_pixel[x, y]
			next_pixel_color = im_pixel[x + 1, y]

			if current_pixel_color[0] > 240 and current_pixel_color[1] > 240 and current_pixel_color[2] > 240 and first_pixel == None:
				first_pixel = (x + 1, y)

			if ((next_pixel_color[0] + 10 < current_pixel_color[0] or next_pixel_color[0] -10 > current_pixel_color[0]) and
				(next_pixel_color[1] + 10 < current_pixel_color[1] or next_pixel_color[1] -10 > current_pixel_color[1]) and
				(next_pixel_color[2] + 10 < current_pixel_color[2] or next_pixel_color[2] -10 > current_pixel_color[2])) and first_pixel != None:
				second_pixel = (x, y)

			if first_pixel != None and second_pixel != None and (second_pixel[0] - first_pixel[0]) > w * 0.7:
				return True
			elif first_pixel != None and second_pixel != None:
				break
	return False


def main():
	
	Game_Start = False
	chess_board_unfound = 0
	#stopwatch.start()

	while True:
		
		if chess_board_unfound > 10:
			chess_board_unfound = 0
		opponent_found = find_opponent()
	
		while not Game_Start and opponent_found and chess_board_unfound <= 10:
			chess_board.reset()
			screencap1.pull_screenshot()
			board_info, Piece_color = create_chess_board_nodes(screencap1.image_taken)
			if board_info is not None and Piece_color is not None:
				#stopwatch.reset()
				Game_Start = True
			
			if Piece_color == 'White':
				engine_make_move(board_info)
			
			chess_board_unfound += 1

		while Game_Start:
			
			screencap2.pull_screenshot()

			if opponent_make_move(screencap1.image_taken, screencap2.image_taken, board_info, Piece_color):
				engine_make_move(board_info)

				if info_handler.info['score'][1].mate is not None and info_handler.info['score'][1].mate <= 3:
					try:
						chess_board.push_uci(info_handler.info['pv'][1][1].uci())
						os.system('cls')
						print('Opponent\'s move ==> \t{}\n'.format(opponent_move_uci))
						print(chess_board)
						engine_make_move(board_info)
					except:
						pass
				screencap1.pull_screenshot()

			if chess_board.is_checkmate() or abortion_or_resignation(screencap2.image_taken): 
				print('\n\nGame Ended')
				stopwatch.stop()
				chess_board_unfound = 0
				Game_Start = False
				time.sleep(1)
				break
			

		

if __name__ == '__main__':
	main()


