#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup as BS
import json as JSON
from os.path import exists
from math import log
from datetime import date
from time import mktime

class Pyrdle(object):

	base_url = "https://qntm.org/files/absurdle/"
	mainpage = "absurdle.html"

	default_file = "./words.dat"

	W = 0
	Y = 1
	G = 2

	def __init__(self, loc=None):

		if loc is None:
			location = self.default_file
		else:
			location = loc

		if exists(location):
			self.read_from_file(location)

		else:
			self.fetch_and_build_wordlist(location)

		# Pre-build responses map.
		responses = [""]
		
		for pos in range(5):
			
			new_responses = []
			
			for stub in responses:
				for option in [str(self.W), str(self.Y), str(self.G)]:
					new_responses.append(stub + option)

			responses = new_responses

		self.response_scores = { r : self.calculate_result_score(r) for r in responses }

		self.reset()

	def calculate_result_score(self, result):

		as_nums = [ int(x) for x in result ]
		
		score = 0
		for i in range(5):

			current_value = as_nums[i]
			score += pow(10, (5+current_value))  +  (current_value * pow(10, (5-i-1)))

		return score

	def score_response(self, response):
		return self.response_scores[response]

	def response_to_emoji(self, result):
		
		s = ""
		
		for c in result:
			if c == str(self.W):
				s += "⬜"
			elif c == str(self.Y):
				s += "🟨"
			elif c == str(self.G):
				s += "🟩"
			else:
				s+= "❓"
		
		return s

	def fetch_and_build_wordlist(self, output=None):

		r = requests.get(self.base_url + self.mainpage)
		html_page = BS(r.text, features="html.parser")

		# Get JS link
		try:
			js_elem = html_page.find_all(defer="defer")[0]
			js_loc = js_elem["src"]
		except:
			raise IOError("Could not find link to JS in page.")

		# Get JS
		r = requests.get(self.base_url + js_loc)

		# Build array of all words (janky but whatever)
		json_frags = r.text.split("N({", 1)[1]
		json1, json_frags = json_frags.split("})", 1)

		json_frags = json_frags.split("N({", 1)[1]
		json2 = json_frags.split("})", 1)[0]

		secret_words = JSON.loads('{"' + json1.replace(',', ',"').replace(':', '":') + "}")
		possible_words = JSON.loads('{"' + json2.replace(',', ',"').replace(':', '":') + "}")

		self.secret_words = self.create_flat_wordlist(secret_words)
		self.possible_words = self.create_flat_wordlist(possible_words)

		if output is not None:

			with open(output, "w") as f:

				f.write(",".join(self.secret_words) + "\n")
				f.write(",".join(self.possible_words))

		self.possible_words += self.secret_words

	def read_from_file(self,inf=None):

		with open(inf, "r") as f:

			l = f.readlines()

		self.secret_words = l[0].split(",")
		self.possible_words = l[1].split(",") + self.secret_words

	def reset(self):

		self.candidates = self.secret_words

	def create_flat_wordlist(self, D):

		made_words = []

		for k in D:

			s = D[k]

			for i in range(0, len(s), 3):
				made_words.append(k + s[i:i+3])

		return made_words

	# This be what absurdle do.
	def find_adversarial_match(self,matches):

		biggest_key = None
		biggest_set_size = -1

		for result in matches:

			set_size = len(matches[result])

			if set_size > biggest_set_size:

				biggest_key = result
				biggest_set_size = set_size

			elif set_size == biggest_set_size:

				if self.score_response(result) < self.score_response(biggest_key):

					biggest_key = result
					biggest_set_size = set_size

		return biggest_key


	# This also be what absurdle do.
	def adversarial_match(self, word):

		if word not in self.possible_words:
			return None

		else:
			matches = self.match_single(word)

			biggest_key = self.find_adversarial_match(matches)

			self.candidates = matches[biggest_key]
			return biggest_key



	# Make response pools for a single word.
	def match_single(self, guess):

		matches = {}

		keys = [""]
		for i in range(5):

			new_keys = []

			for k in keys:
				for c in [self.W, self.G, self.Y]:
					new_keys.append(str(k) + str(c))

			keys = new_keys


		for k in keys:
			matches[k] = []

		for word in self.candidates:

			v = [None] * 5

			for i in range(5):

				if guess[i] == word[i]:
					v[i] = self.G

				elif guess[i] not in word:
					v[i] = self.W

			if None in v:

				for i in range(5):

					if guess[i] in word:
						if v[i] is None:

							matches_thus_far = [ v[j] for j in range(5) if (guess[j] == guess[i] and v[j] is not None) ]
							num_in_candidate = word.count(guess[i])

							if len(matches_thus_far) < num_in_candidate:
								v[i] = self.Y
							else:
								v[i] = self.W



			matches["".join( str(i) for i in v )].append(word)

		return matches

	def print_matches(self, matches):

		printouts = []

		for match in matches:
			
			size = len(matches[match])
			
			s = f"response {self.response_to_emoji(match)} would leave {size:4d}, with a score of {self.result_score(match)}"

			printouts.append((size, s))

		
		printouts.sort(key=lambda x : x[0])
		for p in printouts:
			print (p[1])

	# A first heuristic. Let's see how well it does...
	def greedy_search(self, hardmode=None):

		self.reset()

		solved = False
		
		found = []

		while not solved:

			next_guess = self.greedy_search_single(hardmode)

			print(next_guess)
			found.append(next_guess)

			result = self.adversarial_match(next_guess)

			solved = result == str(self.G) * 5

		return found

	def greedy_search_single(self, hardmode=None):

		best_word = None
		best_set_size = None
		best_score = None

		# See which guess reduces the set of possible (secret) words the most.
		for guess in self.possible_words:

			matches = self.match_single(guess)
			match = self.find_adversarial_match(matches)

			#If the set chosen by Absurdle doesn't contain the hardmode word,
			#don't bother with this guess.
			if hardmode is not None:
				if hardmode not in matches[match]:
					continue

			set_size = len(matches[match])
			score = self.score_response(match)

			if (best_set_size is None) or (set_size < best_set_size) or ((set_size == best_set_size) and (score > best_score)):

				best_word = guess
				best_set_size = set_size
				best_score = score

		return best_word

	def greedy_search_top_n(self, n, hardmode=None):

		best_words = []

		# See which guess reduces the set of possible (secret) words the most.
		for guess in self.possible_words:

			matches = self.match_single(guess)
			match = self.find_adversarial_match(matches)
			
			#If the set chosen by Absurdle doesn't contain the hardmode word,
			#don't bother with this guess.
			if hardmode is not None:
				if hardmode not in matches[match]:
					continue

			set_size = len(matches[match])
			score = self.score_response(match)

			unit = (guess, set_size, score, matches[match])

			if len(best_words) < n:

				best_words.append(unit)
				best_words.sort(key=lambda x : (x[1], x[2]))

			elif (set_size <= best_words[-1][1]):

				best_words.append(unit)
				best_words.sort(key=lambda x : (x[1], x[2]))
				best_words.pop(-1)


		return best_words

	def recurse_tree_with_pruning(self, hardmode=None, width=20):

		class Path(object):

			def __init__(selfp, path=None):

				if path is None:

					selfp.guesses = []
					selfp.pool = self.secret_words[:]

				else:

					selfp.guesses = path.guesses[:]
					selfp.pool = path.pool[:]

			def converged(self):

				return len(self.pool) == 1

			def update(self, guess, new_pool):

				self.guesses.append(guess)
				self.pool = new_pool[:]

		paths = [Path()]

		while not any( path.converged() for path in paths ):

			new_paths = []

			for path in paths:

				self.candidates = path.pool
				best_words = self.greedy_search_top_n(width, hardmode)

				for unit in best_words:

					new_path = Path(path)
					new_path.update(unit[0], unit[3])

					new_paths.append(new_path)

			paths = new_paths
			paths.sort(key=lambda p : len(p.pool))
			paths = paths[:width]

		for i in paths:
			if i.converged():
			   return(i.guesses + i.pool)

	@staticmethod
	def do_wordle():
		
		secret_words = ['CIGAR', 'REBUT', 'SISSY', 'HUMPH', 'AWAKE', 'BLUSH', 'FOCAL', 'EVADE', 'NAVAL', 'SERVE', 'HEATH', 'DWARF', 'MODEL', 'KARMA', 'STINK', 'GRADE', 'QUIET', 'BENCH', 'ABATE', 'FEIGN', 'MAJOR', 'DEATH', 'FRESH', 'CRUST', 'STOOL', 'COLON', 'ABASE', 'MARRY', 'REACT', 'BATTY', 'PRIDE', 'FLOSS', 'HELIX', 'CROAK', 'STAFF', 'PAPER', 'UNFED', 'WHELP', 'TRAWL', 'OUTDO', 'ADOBE', 'CRAZY', 'SOWER', 'REPAY', 'DIGIT', 'CRATE', 'CLUCK', 'SPIKE', 'MIMIC', 'POUND', 'MAXIM', 'LINEN', 'UNMET', 'FLESH', 'BOOBY', 'FORTH', 'FIRST', 'STAND', 'BELLY', 'IVORY', 'SEEDY', 'PRINT', 'YEARN', 'DRAIN', 'BRIBE', 'STOUT', 'PANEL', 'CRASS', 'FLUME', 'OFFAL', 'AGREE', 'ERROR', 'SWIRL', 'ARGUE', 'BLEED', 'DELTA', 'FLICK', 'TOTEM', 'WOOER', 'FRONT', 'SHRUB', 'PARRY', 'BIOME', 'LAPEL', 'START', 'GREET', 'GONER', 'GOLEM', 'LUSTY', 'LOOPY', 'ROUND', 'AUDIT', 'LYING', 'GAMMA', 'LABOR', 'ISLET', 'CIVIC', 'FORGE', 'CORNY', 'MOULT', 'BASIC', 'SALAD', 'AGATE', 'SPICY', 'SPRAY', 'ESSAY', 'FJORD', 'SPEND', 'KEBAB', 'GUILD', 'ABACK', 'MOTOR', 'ALONE', 'HATCH', 'HYPER', 'THUMB', 'DOWRY', 'OUGHT', 'BELCH', 'DUTCH', 'PILOT', 'TWEED', 'COMET', 'JAUNT', 'ENEMA', 'STEED', 'ABYSS', 'GROWL', 'FLING', 'DOZEN', 'BOOZY', 'ERODE', 'WORLD', 'GOUGE', 'CLICK', 'BRIAR', 'GREAT', 'ALTAR', 'PULPY', 'BLURT', 'COAST', 'DUCHY', 'GROIN', 'FIXER', 'GROUP', 'ROGUE', 'BADLY', 'SMART', 'PITHY', 'GAUDY', 'CHILL', 'HERON', 'VODKA', 'FINER', 'SURER', 'RADIO', 'ROUGE', 'PERCH', 'RETCH', 'WROTE', 'CLOCK', 'TILDE', 'STORE', 'PROVE', 'BRING', 'SOLVE', 'CHEAT', 'GRIME', 'EXULT', 'USHER', 'EPOCH', 'TRIAD', 'BREAK', 'RHINO', 'VIRAL', 'CONIC', 'MASSE', 'SONIC', 'VITAL', 'TRACE', 'USING', 'PEACH', 'CHAMP', 'BATON', 'BRAKE', 'PLUCK', 'CRAZE', 'GRIPE', 'WEARY', 'PICKY', 'ACUTE', 'FERRY', 'ASIDE', 'TAPIR', 'TROLL', 'UNIFY', 'REBUS', 'BOOST', 'TRUSS', 'SIEGE', 'TIGER', 'BANAL', 'SLUMP', 'CRANK', 'GORGE', 'QUERY', 'DRINK', 'FAVOR', 'ABBEY', 'TANGY', 'PANIC', 'SOLAR', 'SHIRE', 'PROXY', 'POINT', 'ROBOT', 'PRICK', 'WINCE', 'CRIMP', 'KNOLL', 'SUGAR', 'WHACK', 'MOUNT', 'PERKY', 'COULD', 'WRUNG', 'LIGHT', 'THOSE', 'MOIST', 'SHARD', 'PLEAT', 'ALOFT', 'SKILL', 'ELDER', 'FRAME', 'HUMOR', 'PAUSE', 'ULCER', 'ULTRA', 'ROBIN', 'CYNIC', 'AGORA', 'AROMA', 'CAULK', 'SHAKE', 'PUPAL', 'DODGE', 'SWILL', 'TACIT', 'OTHER', 'THORN', 'TROVE', 'BLOKE', 'VIVID', 'SPILL', 'CHANT', 'CHOKE', 'RUPEE', 'NASTY', 'MOURN', 'AHEAD', 'BRINE', 'CLOTH', 'HOARD', 'SWEET', 'MONTH', 'LAPSE', 'WATCH', 'TODAY', 'FOCUS', 'SMELT', 'TEASE', 'CATER', 'MOVIE', 'LYNCH', 'SAUTE', 'ALLOW', 'RENEW', 'THEIR', 'SLOSH', 'PURGE', 'CHEST', 'DEPOT', 'EPOXY', 'NYMPH', 'FOUND', 'SHALL', 'HARRY', 'STOVE', 'LOWLY', 'SNOUT', 'TROPE', 'FEWER', 'SHAWL', 'NATAL', 'FIBRE', 'COMMA', 'FORAY', 'SCARE', 'STAIR', 'BLACK', 'SQUAD', 'ROYAL', 'CHUNK', 'MINCE', 'SLAVE', 'SHAME', 'CHEEK', 'AMPLE', 'FLAIR', 'FOYER', 'CARGO', 'OXIDE', 'PLANT', 'OLIVE', 'INERT', 'ASKEW', 'HEIST', 'SHOWN', 'ZESTY', 'HASTY', 'TRASH', 'FELLA', 'LARVA', 'FORGO', 'STORY', 'HAIRY', 'TRAIN', 'HOMER', 'BADGE', 'MIDST', 'CANNY', 'FETUS', 'BUTCH', 'FARCE', 'SLUNG', 'TIPSY', 'METAL', 'YIELD', 'DELVE', 'BEING', 'SCOUR', 'GLASS', 'GAMER', 'SCRAP', 'MONEY', 'HINGE', 'ALBUM', 'VOUCH', 'ASSET', 'TIARA', 'CREPT', 'BAYOU', 'ATOLL', 'MANOR', 'CREAK', 'SHOWY', 'PHASE', 'FROTH', 'DEPTH', 'GLOOM', 'FLOOD', 'TRAIT', 'GIRTH', 'PIETY', 'PAYER', 'GOOSE', 'FLOAT', 'DONOR', 'ATONE', 'PRIMO', 'APRON', 'BLOWN', 'CACAO', 'LOSER', 'INPUT', 'GLOAT', 'AWFUL', 'BRINK', 'SMITE', 'BEADY', 'RUSTY', 'RETRO', 'DROLL', 'GAWKY', 'HUTCH', 'PINTO', 'GAILY', 'EGRET', 'LILAC', 'SEVER', 'FIELD', 'FLUFF', 'HYDRO', 'FLACK', 'AGAPE', 'WENCH', 'VOICE', 'STEAD', 'STALK', 'BERTH', 'MADAM', 'NIGHT', 'BLAND', 'LIVER', 'WEDGE', 'AUGUR', 'ROOMY', 'WACKY', 'FLOCK', 'ANGRY', 'BOBBY', 'TRITE', 'APHID', 'TRYST', 'MIDGE', 'POWER', 'ELOPE', 'CINCH', 'MOTTO', 'STOMP', 'UPSET', 'BLUFF', 'CRAMP', 'QUART', 'COYLY', 'YOUTH', 'RHYME', 'BUGGY', 'ALIEN', 'SMEAR', 'UNFIT', 'PATTY', 'CLING', 'GLEAN', 'LABEL', 'HUNKY', 'KHAKI', 'POKER', 'GRUEL', 'TWICE', 'TWANG', 'SHRUG', 'TREAT', 'UNLIT', 'WASTE', 'MERIT', 'WOVEN', 'OCTAL', 'NEEDY', 'CLOWN', 'WIDOW', 'IRONY', 'RUDER', 'GAUZE', 'CHIEF', 'ONSET', 'PRIZE', 'FUNGI', 'CHARM', 'GULLY', 'INTER', 'WHOOP', 'TAUNT', 'LEERY', 'CLASS', 'THEME', 'LOFTY', 'TIBIA', 'BOOZE', 'ALPHA', 'THYME', 'ECLAT', 'DOUBT', 'PARER', 'CHUTE', 'STICK', 'TRICE', 'ALIKE', 'SOOTH', 'RECAP', 'SAINT', 'LIEGE', 'GLORY', 'GRATE', 'ADMIT', 'BRISK', 'SOGGY', 'USURP', 'SCALD', 'SCORN', 'LEAVE', 'TWINE', 'STING', 'BOUGH', 'MARSH', 'SLOTH', 'DANDY', 'VIGOR', 'HOWDY', 'ENJOY', 'VALID', 'IONIC', 'EQUAL', 'UNSET', 'FLOOR', 'CATCH', 'SPADE', 'STEIN', 'EXIST', 'QUIRK', 'DENIM', 'GROVE', 'SPIEL', 'MUMMY', 'FAULT', 'FOGGY', 'FLOUT', 'CARRY', 'SNEAK', 'LIBEL', 'WALTZ', 'APTLY', 'PINEY', 'INEPT', 'ALOUD', 'PHOTO', 'DREAM', 'STALE', 'VOMIT', 'OMBRE', 'FANNY', 'UNITE', 'SNARL', 'BAKER', 'THERE', 'GLYPH', 'POOCH', 'HIPPY', 'SPELL', 'FOLLY', 'LOUSE', 'GULCH', 'VAULT', 'GODLY', 'THREW', 'FLEET', 'GRAVE', 'INANE', 'SHOCK', 'CRAVE', 'SPITE', 'VALVE', 'SKIMP', 'CLAIM', 'RAINY', 'MUSTY', 'PIQUE', 'DADDY', 'QUASI', 'ARISE', 'AGING', 'VALET', 'OPIUM', 'AVERT', 'STUCK', 'RECUT', 'MULCH', 'GENRE', 'PLUME', 'RIFLE', 'COUNT', 'INCUR', 'TOTAL', 'WREST', 'MOCHA', 'DETER', 'STUDY', 'LOVER', 'SAFER', 'RIVET', 'FUNNY', 'SMOKE', 'MOUND', 'UNDUE', 'SEDAN', 'PAGAN', 'SWINE', 'GUILE', 'GUSTY', 'EQUIP', 'TOUGH', 'CANOE', 'CHAOS', 'COVET', 'HUMAN', 'UDDER', 'LUNCH', 'BLAST', 'STRAY', 'MANGA', 'MELEE', 'LEFTY', 'QUICK', 'PASTE', 'GIVEN', 'OCTET', 'RISEN', 'GROAN', 'LEAKY', 'GRIND', 'CARVE', 'LOOSE', 'SADLY', 'SPILT', 'APPLE', 'SLACK', 'HONEY', 'FINAL', 'SHEEN', 'EERIE', 'MINTY', 'SLICK', 'DERBY', 'WHARF', 'SPELT', 'COACH', 'ERUPT', 'SINGE', 'PRICE', 'SPAWN', 'FAIRY', 'JIFFY', 'FILMY', 'STACK', 'CHOSE', 'SLEEP', 'ARDOR', 'NANNY', 'NIECE', 'WOOZY', 'HANDY', 'GRACE', 'DITTO', 'STANK', 'CREAM', 'USUAL', 'DIODE', 'VALOR', 'ANGLE', 'NINJA', 'MUDDY', 'CHASE', 'REPLY', 'PRONE', 'SPOIL', 'HEART', 'SHADE', 'DINER', 'ARSON', 'ONION', 'SLEET', 'DOWEL', 'COUCH', 'PALSY', 'BOWEL', 'SMILE', 'EVOKE', 'CREEK', 'LANCE', 'EAGLE', 'IDIOT', 'SIREN', 'BUILT', 'EMBED', 'AWARD', 'DROSS', 'ANNUL', 'GOODY', 'FROWN', 'PATIO', 'LADEN', 'HUMID', 'ELITE', 'LYMPH', 'EDIFY', 'MIGHT', 'RESET', 'VISIT', 'GUSTO', 'PURSE', 'VAPOR', 'CROCK', 'WRITE', 'SUNNY', 'LOATH', 'CHAFF', 'SLIDE', 'QUEER', 'VENOM', 'STAMP', 'SORRY', 'STILL', 'ACORN', 'APING', 'PUSHY', 'TAMER', 'HATER', 'MANIA', 'AWOKE', 'BRAWN', 'SWIFT', 'EXILE', 'BIRCH', 'LUCKY', 'FREER', 'RISKY', 'GHOST', 'PLIER', 'LUNAR', 'WINCH', 'SNARE', 'NURSE', 'HOUSE', 'BORAX', 'NICER', 'LURCH', 'EXALT', 'ABOUT', 'SAVVY', 'TOXIN', 'TUNIC', 'PRIED', 'INLAY', 'CHUMP', 'LANKY', 'CRESS', 'EATER', 'ELUDE', 'CYCLE', 'KITTY', 'BOULE', 'MORON', 'TENET', 'PLACE', 'LOBBY', 'PLUSH', 'VIGIL', 'INDEX', 'BLINK', 'CLUNG', 'QUALM', 'CROUP', 'CLINK', 'JUICY', 'STAGE', 'DECAY', 'NERVE', 'FLIER', 'SHAFT', 'CROOK', 'CLEAN', 'CHINA', 'RIDGE', 'VOWEL', 'GNOME', 'SNUCK', 'ICING', 'SPINY', 'RIGOR', 'SNAIL', 'FLOWN', 'RABID', 'PROSE', 'THANK', 'POPPY', 'BUDGE', 'FIBER', 'MOLDY', 'DOWDY', 'KNEEL', 'TRACK', 'CADDY', 'QUELL', 'DUMPY', 'PALER', 'SWORE', 'REBAR', 'SCUBA', 'SPLAT', 'FLYER', 'HORNY', 'MASON', 'DOING', 'OZONE', 'AMPLY', 'MOLAR', 'OVARY', 'BESET', 'QUEUE', 'CLIFF', 'MAGIC', 'TRUCE', 'SPORT', 'FRITZ', 'EDICT', 'TWIRL', 'VERSE', 'LLAMA', 'EATEN', 'RANGE', 'WHISK', 'HOVEL', 'REHAB', 'MACAW', 'SIGMA', 'SPOUT', 'VERVE', 'SUSHI', 'DYING', 'FETID', 'BRAIN', 'BUDDY', 'THUMP', 'SCION', 'CANDY', 'CHORD', 'BASIN', 'MARCH', 'CROWD', 'ARBOR', 'GAYLY', 'MUSKY', 'STAIN', 'DALLY', 'BLESS', 'BRAVO', 'STUNG', 'TITLE', 'RULER', 'KIOSK', 'BLOND', 'ENNUI', 'LAYER', 'FLUID', 'TATTY', 'SCORE', 'CUTIE', 'ZEBRA', 'BARGE', 'MATEY', 'BLUER', 'AIDER', 'SHOOK', 'RIVER', 'PRIVY', 'BETEL', 'FRISK', 'BONGO', 'BEGUN', 'AZURE', 'WEAVE', 'GENIE', 'SOUND', 'GLOVE', 'BRAID', 'SCOPE', 'WRYLY', 'ROVER', 'ASSAY', 'OCEAN', 'BLOOM', 'IRATE', 'LATER', 'WOKEN', 'SILKY', 'WRECK', 'DWELT', 'SLATE', 'SMACK', 'SOLID', 'AMAZE', 'HAZEL', 'WRIST', 'JOLLY', 'GLOBE', 'FLINT', 'ROUSE', 'CIVIL', 'VISTA', 'RELAX', 'COVER', 'ALIVE', 'BEECH', 'JETTY', 'BLISS', 'VOCAL', 'OFTEN', 'DOLLY', 'EIGHT', 'JOKER', 'SINCE', 'EVENT', 'ENSUE', 'SHUNT', 'DIVER', 'POSER', 'WORST', 'SWEEP', 'ALLEY', 'CREED', 'ANIME', 'LEAFY', 'BOSOM', 'DUNCE', 'STARE', 'PUDGY', 'WAIVE', 'CHOIR', 'STOOD', 'SPOKE', 'OUTGO', 'DELAY', 'BILGE', 'IDEAL', 'CLASP', 'SEIZE', 'HOTLY', 'LAUGH', 'SIEVE', 'BLOCK', 'MEANT', 'GRAPE', 'NOOSE', 'HARDY', 'SHIED', 'DRAWL', 'DAISY', 'PUTTY', 'STRUT', 'BURNT', 'TULIP', 'CRICK', 'IDYLL', 'VIXEN', 'FUROR', 'GEEKY', 'COUGH', 'NAIVE', 'SHOAL', 'STORK', 'BATHE', 'AUNTY', 'CHECK', 'PRIME', 'BRASS', 'OUTER', 'FURRY', 'RAZOR', 'ELECT', 'EVICT', 'IMPLY', 'DEMUR', 'QUOTA', 'HAVEN', 'CAVIL', 'SWEAR', 'CRUMP', 'DOUGH', 'GAVEL', 'WAGON', 'SALON', 'NUDGE', 'HAREM', 'PITCH', 'SWORN', 'PUPIL', 'EXCEL', 'STONY', 'CABIN', 'UNZIP', 'QUEEN', 'TROUT', 'POLYP', 'EARTH', 'STORM', 'UNTIL', 'TAPER', 'ENTER', 'CHILD', 'ADOPT', 'MINOR', 'FATTY', 'HUSKY', 'BRAVE', 'FILET', 'SLIME', 'GLINT', 'TREAD', 'STEAL', 'REGAL', 'GUEST', 'EVERY', 'MURKY', 'SHARE', 'SPORE', 'HOIST', 'BUXOM', 'INNER', 'OTTER', 'DIMLY', 'LEVEL', 'SUMAC', 'DONUT', 'STILT', 'ARENA', 'SHEET', 'SCRUB', 'FANCY', 'SLIMY', 'PEARL', 'SILLY', 'PORCH', 'DINGO', 'SEPIA', 'AMBLE', 'SHADY', 'BREAD', 'FRIAR', 'REIGN', 'DAIRY', 'QUILL', 'CROSS', 'BROOD', 'TUBER', 'SHEAR', 'POSIT', 'BLANK', 'VILLA', 'SHANK', 'PIGGY', 'FREAK', 'WHICH', 'AMONG', 'FECAL', 'SHELL', 'WOULD', 'ALGAE', 'LARGE', 'RABBI', 'AGONY', 'AMUSE', 'BUSHY', 'COPSE', 'SWOON', 'KNIFE', 'POUCH', 'ASCOT', 'PLANE', 'CROWN', 'URBAN', 'SNIDE', 'RELAY', 'ABIDE', 'VIOLA', 'RAJAH', 'STRAW', 'DILLY', 'CRASH', 'AMASS', 'THIRD', 'TRICK', 'TUTOR', 'WOODY', 'BLURB', 'GRIEF', 'DISCO', 'WHERE', 'SASSY', 'BEACH', 'SAUNA', 'COMIC', 'CLUED', 'CREEP', 'CASTE', 'GRAZE', 'SNUFF', 'FROCK', 'GONAD', 'DRUNK', 'PRONG', 'LURID', 'STEEL', 'HALVE', 'BUYER', 'VINYL', 'UTILE', 'SMELL', 'ADAGE', 'WORRY', 'TASTY', 'LOCAL', 'TRADE', 'FINCH', 'ASHEN', 'MODAL', 'GAUNT', 'CLOVE', 'ENACT', 'ADORN', 'ROAST', 'SPECK', 'SHEIK', 'MISSY', 'GRUNT', 'SNOOP', 'PARTY', 'TOUCH', 'MAFIA', 'EMCEE', 'ARRAY', 'SOUTH', 'VAPID', 'JELLY', 'SKULK', 'ANGST', 'TUBAL', 'LOWER', 'CREST', 'SWEAT', 'CYBER', 'ADORE', 'TARDY', 'SWAMI', 'NOTCH', 'GROOM', 'ROACH', 'HITCH', 'YOUNG', 'ALIGN', 'READY', 'FROND', 'STRAP', 'PUREE', 'REALM', 'VENUE', 'SWARM', 'OFFER', 'SEVEN', 'DRYER', 'DIARY', 'DRYLY', 'DRANK', 'ACRID', 'HEADY', 'THETA', 'JUNTO', 'PIXIE', 'QUOTH', 'BONUS', 'SHALT', 'PENNE', 'AMEND', 'DATUM', 'BUILD', 'PIANO', 'SHELF', 'LODGE', 'SUING', 'REARM', 'CORAL', 'RAMEN', 'WORTH', 'PSALM', 'INFER', 'OVERT', 'MAYOR', 'OVOID', 'GLIDE', 'USAGE', 'POISE', 'RANDY', 'CHUCK', 'PRANK', 'FISHY', 'TOOTH', 'ETHER', 'DROVE', 'IDLER', 'SWATH', 'STINT', 'WHILE', 'BEGAT', 'APPLY', 'SLANG', 'TAROT', 'RADAR', 'CREDO', 'AWARE', 'CANON', 'SHIFT', 'TIMER', 'BYLAW', 'SERUM', 'THREE', 'STEAK', 'ILIAC', 'SHIRK', 'BLUNT', 'PUPPY', 'PENAL', 'JOIST', 'BUNNY', 'SHAPE', 'BEGET', 'WHEEL', 'ADEPT', 'STUNT', 'STOLE', 'TOPAZ', 'CHORE', 'FLUKE', 'AFOOT', 'BLOAT', 'BULLY', 'DENSE', 'CAPER', 'SNEER', 'BOXER', 'JUMBO', 'LUNGE', 'SPACE', 'AVAIL', 'SHORT', 'SLURP', 'LOYAL', 'FLIRT', 'PIZZA', 'CONCH', 'TEMPO', 'DROOP', 'PLATE', 'BIBLE', 'PLUNK', 'AFOUL', 'SAVOY', 'STEEP', 'AGILE', 'STAKE', 'DWELL', 'KNAVE', 'BEARD', 'AROSE', 'MOTIF', 'SMASH', 'BROIL', 'GLARE', 'SHOVE', 'BAGGY', 'MAMMY', 'SWAMP', 'ALONG', 'RUGBY', 'WAGER', 'QUACK', 'SQUAT', 'SNAKY', 'DEBIT', 'MANGE', 'SKATE', 'NINTH', 'JOUST', 'TRAMP', 'SPURN', 'MEDAL', 'MICRO', 'REBEL', 'FLANK', 'LEARN', 'NADIR', 'MAPLE', 'COMFY', 'REMIT', 'GRUFF', 'ESTER', 'LEAST', 'MOGUL', 'FETCH', 'CAUSE', 'OAKEN', 'AGLOW', 'MEATY', 'GAFFE', 'SHYLY', 'RACER', 'PROWL', 'THIEF', 'STERN', 'POESY', 'ROCKY', 'TWEET', 'WAIST', 'SPIRE', 'GROPE', 'HAVOC', 'PATSY', 'TRULY', 'FORTY', 'DEITY', 'UNCLE', 'SWISH', 'GIVER', 'PREEN', 'BEVEL', 'LEMUR', 'DRAFT', 'SLOPE', 'ANNOY', 'LINGO', 'BLEAK', 'DITTY', 'CURLY', 'CEDAR', 'DIRGE', 'GROWN', 'HORDE', 'DROOL', 'SHUCK', 'CRYPT', 'CUMIN', 'STOCK', 'GRAVY', 'LOCUS', 'WIDER', 'BREED', 'QUITE', 'CHAFE', 'CACHE', 'BLIMP', 'DEIGN', 'FIEND', 'LOGIC', 'CHEAP', 'ELIDE', 'RIGID', 'FALSE', 'RENAL', 'PENCE', 'ROWDY', 'SHOOT', 'BLAZE', 'ENVOY', 'POSSE', 'BRIEF', 'NEVER', 'ABORT', 'MOUSE', 'MUCKY', 'SULKY', 'FIERY', 'MEDIA', 'TRUNK', 'YEAST', 'CLEAR', 'SKUNK', 'SCALP', 'BITTY', 'CIDER', 'KOALA', 'DUVET', 'SEGUE', 'CREME', 'SUPER', 'GRILL', 'AFTER', 'OWNER', 'EMBER', 'REACH', 'NOBLY', 'EMPTY', 'SPEED', 'GIPSY', 'RECUR', 'SMOCK', 'DREAD', 'MERGE', 'BURST', 'KAPPA', 'AMITY', 'SHAKY', 'HOVER', 'CAROL', 'SNORT', 'SYNOD', 'FAINT', 'HAUNT', 'FLOUR', 'CHAIR', 'DETOX', 'SHREW', 'TENSE', 'PLIED', 'QUARK', 'BURLY', 'NOVEL', 'WAXEN', 'STOIC', 'JERKY', 'BLITZ', 'BEEFY', 'LYRIC', 'HUSSY', 'TOWEL', 'QUILT', 'BELOW', 'BINGO', 'WISPY', 'BRASH', 'SCONE', 'TOAST', 'EASEL', 'SAUCY', 'VALUE', 'SPICE', 'HONOR', 'ROUTE', 'SHARP', 'BAWDY', 'RADII', 'SKULL', 'PHONY', 'ISSUE', 'LAGER', 'SWELL', 'URINE', 'GASSY', 'TRIAL', 'FLORA', 'UPPER', 'LATCH', 'WIGHT', 'BRICK', 'RETRY', 'HOLLY', 'DECAL', 'GRASS', 'SHACK', 'DOGMA', 'MOVER', 'DEFER', 'SOBER', 'OPTIC', 'CRIER', 'VYING', 'NOMAD', 'FLUTE', 'HIPPO', 'SHARK', 'DRIER', 'OBESE', 'BUGLE', 'TAWNY', 'CHALK', 'FEAST', 'RUDDY', 'PEDAL', 'SCARF', 'CRUEL', 'BLEAT', 'TIDAL', 'SLUSH', 'SEMEN', 'WINDY', 'DUSTY', 'SALLY', 'IGLOO', 'NERDY', 'JEWEL', 'SHONE', 'WHALE', 'HYMEN', 'ABUSE', 'FUGUE', 'ELBOW', 'CRUMB', 'PANSY', 'WELSH', 'SYRUP', 'TERSE', 'SUAVE', 'GAMUT', 'SWUNG', 'DRAKE', 'FREED', 'AFIRE', 'SHIRT', 'GROUT', 'ODDLY', 'TITHE', 'PLAID', 'DUMMY', 'BROOM', 'BLIND', 'TORCH', 'ENEMY', 'AGAIN', 'TYING', 'PESKY', 'ALTER', 'GAZER', 'NOBLE', 'ETHOS', 'BRIDE', 'EXTOL', 'DECOR', 'HOBBY', 'BEAST', 'IDIOM', 'UTTER', 'THESE', 'SIXTH', 'ALARM', 'ERASE', 'ELEGY', 'SPUNK', 'PIPER', 'SCALY', 'SCOLD', 'HEFTY', 'CHICK', 'SOOTY', 'CANAL', 'WHINY', 'SLASH', 'QUAKE', 'JOINT', 'SWEPT', 'PRUDE', 'HEAVY', 'WIELD', 'FEMME', 'LASSO', 'MAIZE', 'SHALE', 'SCREW', 'SPREE', 'SMOKY', 'WHIFF', 'SCENT', 'GLADE', 'SPENT', 'PRISM', 'STOKE', 'RIPER', 'ORBIT', 'COCOA', 'GUILT', 'HUMUS', 'SHUSH', 'TABLE', 'SMIRK', 'WRONG', 'NOISY', 'ALERT', 'SHINY', 'ELATE', 'RESIN', 'WHOLE', 'HUNCH', 'PIXEL', 'POLAR', 'HOTEL', 'SWORD', 'CLEAT', 'MANGO', 'RUMBA', 'PUFFY', 'FILLY', 'BILLY', 'LEASH', 'CLOUT', 'DANCE', 'OVATE', 'FACET', 'CHILI', 'PAINT', 'LINER', 'CURIO', 'SALTY', 'AUDIO', 'SNAKE', 'FABLE', 'CLOAK', 'NAVEL', 'SPURT', 'PESTO', 'BALMY', 'FLASH', 'UNWED', 'EARLY', 'CHURN', 'WEEDY', 'STUMP', 'LEASE', 'WITTY', 'WIMPY', 'SPOOF', 'SANER', 'BLEND', 'SALSA', 'THICK', 'WARTY', 'MANIC', 'BLARE', 'SQUIB', 'SPOON', 'PROBE', 'CREPE', 'KNACK', 'FORCE', 'DEBUT', 'ORDER', 'HASTE', 'TEETH', 'AGENT', 'WIDEN', 'ICILY', 'SLICE', 'INGOT', 'CLASH', 'JUROR', 'BLOOD', 'ABODE', 'THROW', 'UNITY', 'PIVOT', 'SLEPT', 'TROOP', 'SPARE', 'SEWER', 'PARSE', 'MORPH', 'CACTI', 'TACKY', 'SPOOL', 'DEMON', 'MOODY', 'ANNEX', 'BEGIN', 'FUZZY', 'PATCH', 'WATER', 'LUMPY', 'ADMIN', 'OMEGA', 'LIMIT', 'TABBY', 'MACHO', 'AISLE', 'SKIFF', 'BASIS', 'PLANK', 'VERGE', 'BOTCH', 'CRAWL', 'LOUSY', 'SLAIN', 'CUBIC', 'RAISE', 'WRACK', 'GUIDE', 'FOIST', 'CAMEO', 'UNDER', 'ACTOR', 'REVUE', 'FRAUD', 'HARPY', 'SCOOP', 'CLIMB', 'REFER', 'OLDEN', 'CLERK', 'DEBAR', 'TALLY', 'ETHIC', 'CAIRN', 'TULLE', 'GHOUL', 'HILLY', 'CRUDE', 'APART', 'SCALE', 'OLDER', 'PLAIN', 'SPERM', 'BRINY', 'ABBOT', 'RERUN', 'QUEST', 'CRISP', 'BOUND', 'BEFIT', 'DRAWN', 'SUITE', 'ITCHY', 'CHEER', 'BAGEL', 'GUESS', 'BROAD', 'AXIOM', 'CHARD', 'CAPUT', 'LEANT', 'HARSH', 'CURSE', 'PROUD', 'SWING', 'OPINE', 'TASTE', 'LUPUS', 'GUMBO', 'MINER', 'GREEN', 'CHASM', 'LIPID', 'TOPIC', 'ARMOR', 'BRUSH', 'CRANE', 'MURAL', 'ABLED', 'HABIT', 'BOSSY', 'MAKER', 'DUSKY', 'DIZZY', 'LITHE', 'BROOK', 'JAZZY', 'FIFTY', 'SENSE', 'GIANT', 'SURLY', 'LEGAL', 'FATAL', 'FLUNK', 'BEGAN', 'PRUNE', 'SMALL', 'SLANT', 'SCOFF', 'TORUS', 'NINNY', 'COVEY', 'VIPER', 'TAKEN', 'MORAL', 'VOGUE', 'OWING', 'TOKEN', 'ENTRY', 'BOOTH', 'VOTER', 'CHIDE', 'ELFIN', 'EBONY', 'NEIGH', 'MINIM', 'MELON', 'KNEED', 'DECOY', 'VOILA', 'ANKLE', 'ARROW', 'MUSHY', 'TRIBE', 'CEASE', 'EAGER', 'BIRTH', 'GRAPH', 'ODDER', 'TERRA', 'WEIRD', 'TRIED', 'CLACK', 'COLOR', 'ROUGH', 'WEIGH', 'UNCUT', 'LADLE', 'STRIP', 'CRAFT', 'MINUS', 'DICEY', 'TITAN', 'LUCID', 'VICAR', 'DRESS', 'DITCH', 'GYPSY', 'PASTA', 'TAFFY', 'FLAME', 'SWOOP', 'ALOOF', 'SIGHT', 'BROKE', 'TEARY', 'CHART', 'SIXTY', 'WORDY', 'SHEER', 'LEPER', 'NOSEY', 'BULGE', 'SAVOR', 'CLAMP', 'FUNKY', 'FOAMY', 'TOXIC', 'BRAND', 'PLUMB', 'DINGY', 'BUTTE', 'DRILL', 'TRIPE', 'BICEP', 'TENOR', 'KRILL', 'WORSE', 'DRAMA', 'HYENA', 'THINK', 'RATIO', 'COBRA', 'BASIL', 'SCRUM', 'BUSED', 'PHONE', 'COURT', 'CAMEL', 'PROOF', 'HEARD', 'ANGEL', 'PETAL', 'POUTY', 'THROB', 'MAYBE', 'FETAL', 'SPRIG', 'SPINE', 'SHOUT', 'CADET', 'MACRO', 'DODGY', 'SATYR', 'RARER', 'BINGE', 'TREND', 'NUTTY', 'LEAPT', 'AMISS', 'SPLIT', 'MYRRH', 'WIDTH', 'SONAR', 'TOWER', 'BARON', 'FEVER', 'WAVER', 'SPARK', 'BELIE', 'SLOOP', 'EXPEL', 'SMOTE', 'BALER', 'ABOVE', 'NORTH', 'WAFER', 'SCANT', 'FRILL', 'AWASH', 'SNACK', 'SCOWL', 'FRAIL', 'DRIFT', 'LIMBO', 'FENCE', 'MOTEL', 'OUNCE', 'WREAK', 'REVEL', 'TALON', 'PRIOR', 'KNELT', 'CELLO', 'FLAKE', 'DEBUG', 'ANODE', 'CRIME', 'SALVE', 'SCOUT', 'IMBUE', 'PINKY', 'STAVE', 'VAGUE', 'CHOCK', 'FIGHT', 'VIDEO', 'STONE', 'TEACH', 'CLEFT', 'FROST', 'PRAWN', 'BOOTY', 'TWIST', 'APNEA', 'STIFF', 'PLAZA', 'LEDGE', 'TWEAK', 'BOARD', 'GRANT', 'MEDIC', 'BACON', 'CABLE', 'BRAWL', 'SLUNK', 'RASPY', 'FORUM', 'DRONE', 'WOMEN', 'MUCUS', 'BOAST', 'TODDY', 'COVEN', 'TUMOR', 'TRUER', 'WRATH', 'STALL', 'STEAM', 'AXIAL', 'PURER', 'DAILY', 'TRAIL', 'NICHE', 'MEALY', 'JUICE', 'NYLON', 'PLUMP', 'MERRY', 'FLAIL', 'PAPAL', 'WHEAT', 'BERRY', 'COWER', 'ERECT', 'BRUTE', 'LEGGY', 'SNIPE', 'SINEW', 'SKIER', 'PENNY', 'JUMPY', 'RALLY', 'UMBRA', 'SCARY', 'MODEM', 'GROSS', 'AVIAN', 'GREED', 'SATIN', 'TONIC', 'PARKA', 'SNIFF', 'LIVID', 'STARK', 'TRUMP', 'GIDDY', 'REUSE', 'TABOO', 'AVOID', 'QUOTE', 'DEVIL', 'LIKEN', 'GLOSS', 'GAYER', 'BERET', 'NOISE', 'GLAND', 'DEALT', 'SLING', 'RUMOR', 'OPERA', 'THIGH', 'TONGA', 'FLARE', 'WOUND', 'WHITE', 'BULKY', 'ETUDE', 'HORSE', 'CIRCA', 'PADDY', 'INBOX', 'FIZZY', 'GRAIN', 'EXERT', 'SURGE', 'GLEAM', 'BELLE', 'SALVO', 'CRUSH', 'FRUIT', 'SAPPY', 'TAKER', 'TRACT', 'OVINE', 'SPIKY', 'FRANK', 'REEDY', 'FILTH', 'SPASM', 'HEAVE', 'MAMBO', 'RIGHT', 'CLANK', 'TRUST', 'LUMEN', 'BORNE', 'SPOOK', 'SAUCE', 'AMBER', 'LATHE', 'CARAT', 'CORER', 'DIRTY', 'SLYLY', 'AFFIX', 'ALLOY', 'TAINT', 'SHEEP', 'KINKY', 'WOOLY', 'MAUVE', 'FLUNG', 'YACHT', 'FRIED', 'QUAIL', 'BRUNT', 'GRIMY', 'CURVY', 'CAGEY', 'RINSE', 'DEUCE', 'STATE', 'GRASP', 'MILKY', 'BISON', 'GRAFT', 'SANDY', 'BASTE', 'FLASK', 'HEDGE', 'GIRLY', 'SWASH', 'BONEY', 'COUPE', 'ENDOW', 'ABHOR', 'WELCH', 'BLADE', 'TIGHT', 'GEESE', 'MISER', 'MIRTH', 'CLOUD', 'CABAL', 'LEECH', 'CLOSE', 'TENTH', 'PECAN', 'DROIT', 'GRAIL', 'CLONE', 'GUISE', 'RALPH', 'TANGO', 'BIDDY', 'SMITH', 'MOWER', 'PAYEE', 'SERIF', 'DRAPE', 'FIFTH', 'SPANK', 'GLAZE', 'ALLOT', 'TRUCK', 'KAYAK', 'VIRUS', 'TESTY', 'TEPEE', 'FULLY', 'ZONAL', 'METRO', 'CURRY', 'GRAND', 'BANJO', 'AXION', 'BEZEL', 'OCCUR', 'CHAIN', 'NASAL', 'GOOEY', 'FILER', 'BRACE', 'ALLAY', 'PUBIC', 'RAVEN', 'PLEAD', 'GNASH', 'FLAKY', 'MUNCH', 'DULLY', 'EKING', 'THING', 'SLINK', 'HURRY', 'THEFT', 'SHORN', 'PYGMY', 'RANCH', 'WRING', 'LEMON', 'SHORE', 'MAMMA', 'FROZE', 'NEWER', 'STYLE', 'MOOSE', 'ANTIC', 'DROWN', 'VEGAN', 'CHESS', 'GUPPY', 'UNION', 'LEVER', 'LORRY', 'IMAGE', 'CABBY', 'DRUID', 'EXACT', 'TRUTH', 'DOPEY', 'SPEAR', 'CRIED', 'CHIME', 'CRONY', 'STUNK', 'TIMID', 'BATCH', 'GAUGE', 'ROTOR', 'CRACK', 'CURVE', 'LATTE', 'WITCH', 'BUNCH', 'REPEL', 'ANVIL', 'SOAPY', 'METER', 'BROTH', 'MADLY', 'DRIED', 'SCENE', 'KNOWN', 'MAGMA', 'ROOST', 'WOMAN', 'THONG', 'PUNCH', 'PASTY', 'DOWNY', 'KNEAD', 'WHIRL', 'RAPID', 'CLANG', 'ANGER', 'DRIVE', 'GOOFY', 'EMAIL', 'MUSIC', 'STUFF', 'BLEEP', 'RIDER', 'MECCA', 'FOLIO', 'SETUP', 'VERSO', 'QUASH', 'FAUNA', 'GUMMY', 'HAPPY', 'NEWLY', 'FUSSY', 'RELIC', 'GUAVA', 'RATTY', 'FUDGE', 'FEMUR', 'CHIRP', 'FORTE', 'ALIBI', 'WHINE', 'PETTY', 'GOLLY', 'PLAIT', 'FLECK', 'FELON', 'GOURD', 'BROWN', 'THRUM', 'FICUS', 'STASH', 'DECRY', 'WISER', 'JUNTA', 'VISOR', 'DAUNT', 'SCREE', 'IMPEL', 'AWAIT', 'PRESS', 'WHOSE', 'TURBO', 'STOOP', 'SPEAK', 'MANGY', 'EYING', 'INLET', 'CRONE', 'PULSE', 'MOSSY', 'STAID', 'HENCE', 'PINCH', 'TEDDY', 'SULLY', 'SNORE', 'RIPEN', 'SNOWY', 'ATTIC', 'GOING', 'LEACH', 'MOUTH', 'HOUND', 'CLUMP', 'TONAL', 'BIGOT', 'PERIL', 'PIECE', 'BLAME', 'HAUTE', 'SPIED', 'UNDID', 'INTRO', 'BASAL', 'SHINE', 'GECKO', 'RODEO', 'GUARD', 'STEER', 'LOAMY', 'SCAMP', 'SCRAM', 'MANLY', 'HELLO', 'VAUNT', 'ORGAN', 'FERAL', 'KNOCK', 'EXTRA', 'CONDO', 'ADAPT', 'WILLY', 'POLKA', 'RAYON', 'SKIRT', 'FAITH', 'TORSO', 'MATCH', 'MERCY', 'TEPID', 'SLEEK', 'RISER', 'TWIXT', 'PEACE', 'FLUSH', 'CATTY', 'LOGIN', 'EJECT', 'ROGER', 'RIVAL', 'UNTIE', 'REFIT', 'AORTA', 'ADULT', 'JUDGE', 'ROWER', 'ARTSY', 'RURAL', 'SHAVE']

		#Create index into this list
		index = mktime(date.today().timetuple()) - 1624057200
		index = round(index / 86400)
		index = index % len(secret_words)
		
		return secret_words[index]

		"""
		wordURLe = "https://www.powerlanguage.co.uk/wordle/"
		
		# Get wordle main page
		r = requests.get(wordURLe)
		
		if r.status_code != 200:
			print("Could not get today's Wordle.")
			return

		# Get script.
		html_page = BS(r.text, features="html.parser")
		
		# Get JS link
		try:
			js_link = None
			
			js_elem = html_page.find_all("script", attrs={"src" : True})

			for elem in js_elem:
				if elem["src"][:5] == "main.":
					js_link = elem["src"]
					break

			assert(js_link is not None)

		except:
			raise IOError("Could not find link to JS in page.")

		# Get JS
		r = requests.get(wordURLe + js_link)

		# Build array of all secret words (janky but whatever)
		json_frags = r.text.split("var La=", 1)[1]
		json_frags = json_frags.split(",Ta", 1)[0]

		secret_words = JSON.loads(json_frags)
		
		print (secret_words)
		"""
		

		
