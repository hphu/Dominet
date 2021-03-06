"""
This is a wrapper structure to abstract the data structure for hand and supply piles.
"""

import random
import reactionHandler
from tornado import gen

class CardPile():
	def __init__(self):
		# The underlying data is a dictionary with key = cardtitle, value = [card object, count]
		self.data = {}
		self.index = 0

	def add(self, card, count=1):
		if card.title in self.data:
			self.data[card.title] = [card, self.data[card.title][1] + count]
		else:
			self.data[card.title] = [card, count]

	def extract(self, card_title):
		if card_title in self.data:
			self.data[card_title][1] -= 1
			return self.data[card_title][0]
		else:
			print("Error tried to extract card not in cardpile")

	def get_count(self, card_title):
		if card_title not in self.data:
			return 0
		return self.data[card_title][1]

	def get_card(self, card_title):
		return self.data[card_title][0]

	def unique_cards(self):
		return [self.get_card(x) for x in self.data.keys()]

	def card_array(self):
		arr = []
		for title, lst in self.data.items():
			card = lst[0]
			count = lst[1]
			for i in range(0, count):
				arr.append(card)
		return arr

	def to_json(self):
		result = []
		for title, lst in self.data.items():
			formatCard = lst[0].to_json()
			formatCard["count"] = lst[1]
			result.append(formatCard)
		return result

	def __iter__(self):
		return self

	def __next__(self):
		self.index += 1
		index_counter = self.index
		for i in self.data:
			if index_counter <= self.data[i][1]:
				return self.data[i][0]
			else:
				index_counter -= self.data[i][1]
		self.index = 0
		raise StopIteration

	def __len__(self):
		count = 0
		for title, data in self.data.items():
			count += data[1]
		return count

	def __contains__(self, title):
		return title in self.data

	def __str__(self):
		str_list = []
		for key, val in self.data.items():
			str_list.append("{} {}".format(val[1], val[0].log_string()))
		return ", ".join(str_list)

	def combine(self, cardPile):
		self.data.update(cardPile.data.copy())

	def pile_contains(self, price=None, cardtype=None):
		price_exists = False
		cardtype_exists = False
		if price:
			for title in self.data:
				if self.data[title][0].get_price() == price:
					price_exists = True
					break

		if cardtype:
			for title in self.data:
				if cardtype in self.data[title][0].type:
					cardtype_exists = True
					break

		return (not price or price_exists) and (not cardtype or cardtype_exists)

	#returns true if there are available cards left in supply to gain from with the given parameters
	#constraint = function to filter supply selection
	def has_selectable(self, constraint, allow_empty=False):
		return [x for x in self.unique_cards() if constraint(x) and self.get_count(x.title) > 0 or allow_empty]

class HandPile(CardPile):
	def __init__(self, player):
		# The underlying data is a dictionary with key = cardtitle, value = [card object, card object, etc...]
		CardPile.__init__(self)
		self.player = player
		self.data = {}
		self.index = -1
		self.reacthelper = reactionHandler.ReactionHandler(self.player)

	def add(self, card):
		if card.title in self.data:
			self.data[card.title].append(card)
		else:
			self.data[card.title] = [card]

	def extract(self, card_title):
		if card_title in self.data:
			card = self.data[card_title].pop()
			if self.get_count(card.title) == 0:
				del self.data[card.title]
			return card
		else:
			return None

	def extract_specific(self, card):
		if card.title in self.data:
			extracted_card = self.data[card.title].pop(card)
			if self.get_count(card.title) == 0:
				del self.data[card.title]
			return extracted_card
		else:
			return None

	def get_count(self, card_title):
		if card_title not in self.data:
			return 0
		return len(self.data[card_title])

	def get_card(self, card_title):
		return self.data[card_title][-1]

	def get_all(self, card_title):
		return self.data[card_title]

	def card_array(self):
		arr = []
		for title, lst in self.data.items():
			arr += lst
		return arr

	def to_json(self):
		result = []
		for title, lst in self.data.items():
			formatCard = lst[0].to_json()
			formatCard["count"] = len(lst)
			result.append(formatCard)
		return result

	def reveal_string(self):
		h = []
		for title, lst in self.data.items():
			card = lst[0]
			count = len(lst)
			cardstr = str(count)
			logstr = card.log_string(True) if count > 1 else card.log_string()
			cardstr += " " + logstr
			h.append(cardstr)
		return ", ".join(h)

	# returns list of cards of given type
	def get_cards_by_type(self, ctype, include_subtypes=True):
		results = []
		for card in self.card_array():
			if include_subtypes:
				if ctype in card.type:
					results.append(card)
			else:
				if ctype == card.type:
					results.append(card)
		return results

	#returns a list reaction cards in hand with the input trigger
	def get_reactions_for(self, trigger):
		reactions = []
		for card in self:
			if "Reaction" in card.type and trigger == card.trigger:
				reactions.append(card)
		return reactions
		
	#triggers reactions in hand
	@gen.coroutine
	def do_reactions(self, trigger, react_data=None):
		reactions = self.get_reactions_for(trigger)
		if len(reactions) == 0:
			return
		else:
			yield self.reacthelper.initiate_reaction_event(trigger, react_data)

	def is_homogeneous(self):
		return len(self.data) == 1

	def auto_select(self, num_options, allow_less):
		if len(self) < num_options:
			if allow_less:
				return [card.title for card in self]
			else:
				return []
		if self.is_homogeneous():
			card = self.card_array()[0]
			return [card.title for x in range(0, min(len(self.card_array()), num_options))]
		if len(self) == num_options:
			return list(map(lambda x: x.title, self.card_array()))
		return []

	@gen.coroutine
	def play(self, card_title):
		yield gen.maybe_future(self.get_card(card_title).play())

	def __iter__(self):
		return self.card_array().__iter__()

	def __len__(self):
		return len(self.card_array())

	def __contains__(self, title):
		return title in self.data
