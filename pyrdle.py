#!/usr/bin/env python3

import argparse
from random import choice
from time import time

from pyrdle_core import Pyrdle

def play(challenge_mode=False):

	cursor = "> "

	P = Pyrdle()
	
	if challenge_mode:
		target_word = choice(P.secret_words)
		print(f"Target word is: {target_word}\n")
	else:
		target_word = None

	win = str(P.G) * 5
	user_guesses = 1
	while(True):
		
		#Get user guess
		while(True):
			user_guess = input(cursor)
			if len(user_guess) != 5:
				print("Please enter a five-letter word.")
			elif user_guess.upper() not in P.possible_words:
				print("Please enter a valid word.")
			else:
				user_guess = user_guess.upper()
				break
		
		#Make user guess.
		r = P.adversarial_match(user_guess)

		#Display reponse
		print(cursor + P.response_to_emoji(r) + "\n")
		
		if r == win:
			print(f"You won in {user_guesses} guesses!")
			break

		elif target_word is not None:
			
			if target_word not in P.candidates:
				print(f"Target word {target_word} is no longer possible!")
				break

		else:
			user_guesses += 1

def solve(pruning, n, challenge_mode=None):

	cursor = "> "

	P = Pyrdle()
	
	if challenge_mode is not None:
		if (len(challenge_mode) != 5):
			print("Target word must be five letters in length.")
			return
		elif challenge_mode.upper() not in P.secret_words:
			print("Target word must be in the list of secret words:")
			print(", ".join(P.secret_words))
			return
		else:
			challenge_mode = challenge_mode.upper()

	T1 = time()

	if pruning:
		solution = P.recurse_tree_with_pruning(hardmode=challenge_mode, width=n)
	else:
		solution = P.greedy_search(challenge_mode)
	
	T2 = time()
	
	print(f"\nFound the following solution in {(T2 - T1):.6f}s:")
	print(", ".join(solution))
	print("")

def wordle():
	
	s = Pyrdle.do_wordle()
	
	print(f"Today's wordle solution is: {s}")

if __name__ == "__main__":
	
	parser = argparse.ArgumentParser(description="A Python3 reimagining of @qntm's Absurdle. By default, this program will offer an absurdle game for you to play, but you can also use it to generate Absurdle solutions.")
	parser.add_argument("target", nargs="?", default=None, metavar="target", type=str, help="The target word. If supplied, Pyrdle will assume you're solving challenge mode for this word.")
	parser.add_argument("-c", default=False, required=False, action="store_true", help="Enable challenge mode.")
	parser.add_argument("-s", default=False, required=False, action="store_true", help="Find solutions.")
	parser.add_argument("-p", default=False, required=False, action="store_true", help="Use branch pruning. This will take longer to run, but will find better solutions.")
	parser.add_argument("-n", default=20, required=False, type=int, help="Branch pruning width. Defaults to 20 if not set.")
	parser.add_argument("-w", default=False, required=False, action="store_true", help="Get today's Wordle solution.")
	
	args = parser.parse_args()

	# Wordle mode.
	if args.w:
		wordle()

	# Solver mode.
	elif args.s:
		solve(args.p, args.n, args.target)

	# Play mode.
	else:
		play(args.c)
