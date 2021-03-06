import sets.card as crd
import math
import tornado.gen as gen

# --------------------------------------------------------
# ------------------------ 3 Cost ------------------------
# --------------------------------------------------------

class Watchtower(crd.Card):
	def __init__(self, game, played_by):
		crd.Card.__init__(self, game, played_by)
		self.title = "Watchtower"
		self.description = "Draw until you have 6 cards in hand. Whenever you gain a card, you may\
			reveal Watchtower to trash it or put it on top of your deck."
		self.price = 3
		self.type = "Action|Reaction"
		self.trigger = "Gain"

	def play(self, skip=False):
		crd.Card.play(self, skip)
		num_to_draw = 6 - len(self.played_by.hand)
		if num_to_draw > 0:
			drawn = self.played_by.draw(num_to_draw)
			self.game.announce("-- drawing " + drawn)
		else:
			self.game.announce("-- but already has at least 6 cards in hand")
		crd.Card.on_finished(self)

	@gen.coroutine
	def react(self, to_gain):
		self.played_by.wait_modeless("", self.played_by, True)
		reveal_choice = yield self.played_by.select(1, 1, ["Reveal", "Hide"],  
			"Reveal " + self.title + " to trash " + to_gain.title + " or put it on top of deck?")

		if reveal_choice[0] == "Reveal":
			#remove the to_gained card from discard or player's piles
			to_gain = self.played_by.search_and_extract_card(to_gain)
			self.game.announce(self.played_by.name_string() + " reveals " + self.log_string())
			self.played_by.wait_modeless("", self.played_by, True)
			if to_gain:
				selection = yield self.played_by.select(1, 1, ["Trash", "Put on top of deck"], "Choose to trash")
				if selection[0] == "Trash":
					self.game.announce("-- trashing " + to_gain.log_string() + " instead of gaining it")
					self.game.trash_pile.append(to_gain)
					self.game.update_trash_pile()
				else:
					self.game.announce("-- putting " + to_gain.log_string() + " on the top of their deck")
					self.played_by.deck.append(to_gain)
					self.played_by.update_deck_size()
			else:
				self.game.announce("-- but has nothing to watchtower")

	def log_string(self, plural=False):
		return "".join(["<span class='label label-reaction'>", self.title, "s</span>" if plural else "</span>"])

class Loan(crd.Money):
	def __init__(self, game, played_by):
		crd.Money.__init__(self, game, played_by)
		self.title = "Loan"
		self.description = "{}" \
		                   "When you play this, reveal cards from your deck until you reveal a Treasure." \
		                   " Discard it or trash it. Discard the other cards.".format(crd.format_money(1))
		self.price = 3
		self.value = 1
		self.type = "Treasure"
		self.spend_all = False

	@gen.coroutine
	def play(self, skip=False):
		crd.Card.play(self, skip)
		self.played_by.balance += self.value
		self.played_by.update_resources(True)
		found_treasure = yield crd.search_deck_for(self.played_by, lambda x : "Treasure" in x.type)
		if found_treasure is None:
			self.game.announce("-- but could not find any treasures in his or her deck.")
		else:
			self.game.announce("-- revealing " + found_treasure.log_string())

			selection = yield self.played_by.select(1, 1, ["Discard", "Trash"], "Discard or Trash " + found_treasure.title)
			if selection[0] == "Discard":
				yield self.played_by.discard_floating(found_treasure)
				self.game.announce("-- discarding {}".format(found_treasure.log_string()))
			else:
				self.game.trash_pile.append(found_treasure)
				self.game.update_trash_pile()
				self.game.announce("-- trashing {}".format(found_treasure.log_string()))
		crd.Money.on_finished(self)


class Trade_Route(crd.Card):

	def __init__(self, game, played_by):
		crd.Card.__init__(self, game, played_by)
		self.title = "Trade Route"
		self.description = "{}{}Trash a card from your hand. \nX is the number of cards on the Trade Route Mat\n"\
							"static: a Victory card is added to the Trade Route Mat "\
							"when it is gained for the first time from supply".format(crd.format_buys(1), crd.format_money("X"))
		self.price = 3
		self.type = "Action"

	def on_supply_init(self):
		for supply_card in self.game.supply.unique_cards():
			if "Victory" in supply_card.type:
				#Here we store the on_gain function of this card and override it with our own gained_to_mat function
				default_on_gain_function = supply_card.on_gain
				supply_card.on_gain = staticmethod(lambda x=supply_card, y=default_on_gain_function : self.gained_to_mat(x, y))
		self.game.mat["Trade Route Mat"] = []

	#this is set to be the on_gain function for all cards with trade route tokens on it. It increases the mat value
	#when the card is gained the first time and then removes this function as the on_gain and resets it to the previous
	#function.
	@gen.coroutine
	def gained_to_mat(self, supply_card, previous_gain_func):
		if (supply_card.log_string() not in self.game.mat["Trade Route Mat"]):
			self.game.mat["Trade Route Mat"].append(supply_card.log_string())
			self.game.update_mat()
		#call overriden on_gain
		yield previous_gain_func.__get__(supply_card, crd.Card)()

	@gen.coroutine
	def play(self, skip=False):
		crd.Card.play(self, skip)
		mat_value = len(self.game.mat["Trade Route Mat"])
		self.played_by.balance += mat_value
		self.played_by.buys += 1
		self.game.announce("-- gaining a buy and $" + str(mat_value))
		selection = yield self.played_by.select(1, 1, crd.card_list_to_titles(self.played_by.hand.card_array()), "Choose a card to trash")
		if selection:
			trashed = self.played_by.hand.extract(selection[0])
			self.game.announce("-- trashing " + trashed.log_string())
			self.game.trash_pile.append(trashed)
			self.game.update_trash_pile()
		crd.Card.on_finished(self)


# --------------------------------------------------------
# ------------------------ 4 Cost ------------------------
# --------------------------------------------------------


class Bishop(crd.Card):
	def __init__(self, game, played_by):
		crd.Card.__init__(self, game, played_by)
		self.title = "Bishop"
		self.description = "{} +1 VP token\n Trash a card from your hand. +VP tokens equal to half its cost in coins" \
		                   ", rounded down. Each other player may trash a card from his hand.".format(crd.format_money(1))
		self.price = 4
		self.type = "Action"

	@gen.coroutine
	def play(self, skip=False):
		crd.Card.play(self, skip)
		self.played_by.balance += 1
		self.played_by.vp += 1

		self.game.announce("-- gaining +$1 and +1 VP")
		selection = yield self.played_by.select(1, 1, crd.card_list_to_titles(self.played_by.hand.card_array()), "Choose a card to trash")
		if selection:
			trash = self.played_by.hand.extract(selection[0])
			half_vp = math.floor(trash.get_price() / 2)
			self.played_by.vp += half_vp
			self.game.trash_pile.append(trash)
			self.game.update_trash_pile()

			self.played_by.update_hand()

			self.game.announce("-- trashing " + trash.log_string() + " gaining " + str(half_vp) + " VP")
		self.played_by.wait_many("to trash", self.played_by.get_opponents())
		yield self.get_next(self.played_by)

	@gen.coroutine
	def get_next(self, player):
		next_player_index = (self.game.players.index(player) + 1) % len(self.game.players)
		next_player = self.game.players[next_player_index]
		if next_player == self.played_by:
			crd.Card.on_finished(self)
		else:
			selection = yield next_player.select(1, 1, crd.card_list_to_titles(next_player.hand.card_array()) + ["None"],
			                   "Choose a card to trash")
			if selection[0] != "None":
				trash = next_player.hand.extract(selection[0])
				self.game.trash_pile.append(trash)
				self.game.update_trash_pile()
				next_player.update_hand()
				self.game.announce("-- " + next_player.name + " trashes " + trash.log_string())
			yield self.get_next(next_player)

class Monument(crd.Card):
	def __init__(self, game, played_by):
		crd.Card.__init__(self, game, played_by)
		self.title = "Monument"
		self.description = "{}+1 VP token".format(crd.format_money(2))
		self.price = 4
		self.type = "Action"

	def play(self, skip=False):
		crd.Card.play(self, skip)
		self.played_by.balance += 2
		self.played_by.vp += 1
		self.game.announce("-- gaining +$2 and +1 VP")
		crd.Card.on_finished(self)


class Workers_Village(crd.Card):
	def __init__(self, game, played_by):
		crd.Card.__init__(self, game, played_by)
		self.title = "Worker's Village"
		self.description = "{}{}{}".format(crd.format_draw(1), crd.format_actions(2), crd.format_buys(1))
		self.price = 4
		self.type = "Action"

	def play(self, skip=False):
		crd.Card.play(self, skip)
		self.played_by.actions += 2
		self.played_by.buys += 1
		drawn = self.played_by.draw(1)
		self.game.announce("-- drawing " + drawn + " and gaining 2 actions and 1 buy")
		crd.Card.on_finished(self)


class Talisman(crd.Money):
	def __init__(self, game, played_by):
		crd.Money.__init__(self, game, played_by)
		self.title = "Talisman"
		self.description = "{}While this is in play, when you buy a card costing $4 or less" \
		                   " that is not a Victory card, gain a copy of it.".format(crd.format_money(1))
		self.price = 4
		self.value = 1
		self.type = "Treasure"
		self.spend_all = False

	@gen.coroutine
	def on_buy_effect(self, purchased_card):
		if purchased_card.get_price() <= 4 and "Victory" not in purchased_card.type:
			yield self.played_by.gain(purchased_card.title, custom_announce="-- gaining another " + purchased_card.log_string())


class Quarry(crd.Money):
	def __init__(self, game, played_by):
		crd.Money.__init__(self, game, played_by)
		self.title = "Quarry"
		self.description = "{}While this is in play, Action cards cost $2 less" \
		                   " but not less than 0".format(crd.format_money(1))
		self.price = 4
		self.value = 1
		self.type = "Treasure"
		self.spend_all = False

	def play(self, skip=False):
		crd.Money.play(self, skip)
		for x in self.game.price_modifier.keys():
			if "Action" in self.game.card_from_title(x).type:
				self.game.price_modifier[x] -= 2
		self.game.update_all_prices()
		crd.Money.on_finished(self)

	def log_string(self, plural=False):
		return "".join(["<span class='label label-treasure'>", "Quarries</span>" if plural else self.title + "</span>"])


# --------------------------------------------------------
# ------------------------ 5 Cost ------------------------
# --------------------------------------------------------

class City(crd.Card):
	def __init__(self, game, played_by):
		crd.Card.__init__(self, game, played_by)
		self.title = "City"
		self.description = "{}{} " \
		                   "If there are one or more empty Supply piles: {}"\
		                    "If there are two or more: {} {}".format(crd.format_draw(1), 
		                    	crd.format_actions(2), crd.format_draw(1), crd.format_money(1, True), crd.format_buys(1, True))
		self.price = 5
		self.type = "Action"

	def play(self, skip=False):
		crd.Card.play(self, skip)
		self.played_by.actions += 2

		if self.game.empty_piles >= 1:
			drawn = self.played_by.draw(2)
		else:
			drawn = self.played_by.draw(1)

		drawn = "and drawing " + drawn

		if self.game.empty_piles >= 2:
			self.played_by.buys += 1
			self.played_by.balance += 1
			drawn = "+1 buy and +$1 " + drawn

		self.game.announce("-- gaining 2 actions " + drawn)
		crd.Card.on_finished(self)

	def log_string(self, plural=False):
		return "".join(["<span class='label label-action'>", "Cities</span>" if plural else self.title + "</span>"])


class Contraband(crd.Money):
	def __init__(self, game, played_by):
		crd.Card.__init__(self, game, played_by)
		self.title = "Contraband"
		self.description = "{}{}The player to your left names a card, you cannot buy that card this turn.".format(crd.format_money(3), crd.format_buys(1))
		self.price = 5
		self.value = 3
		self.type = "Treasure"
		self.spend_all = False

	@gen.coroutine
	def play(self, skip=False):
		crd.Money.play(self, skip)
		self.played_by.buys += 1
		self.game.announce("-- gaining a buy")
		left_opponent = self.played_by.get_left_opponent()
		self.played_by.wait("to choose a card for contraband", left_opponent)
		banned = yield left_opponent.select_from_supply("Ban a card from " + self.played_by.name)
		self.game.announce(left_opponent.name_string() + " bans " + self.game.log_string_from_title(banned[0]))
		self.played_by.banned.append(banned[0])
		crd.Money.on_finished(self)

class Counting_House(crd.Card):
	def __init__(self, game, played_by):
		crd.Card.__init__(self, game, played_by)
		self.title = "Counting House"
		self.description = "Look through your discard pile, reveal any number of Copper cards from it, and put them into your hand."
		self.price = 5
		self.type = "Action"

	@gen.coroutine
	def play(self, skip=False):
		crd.Card.play(self, skip)
		coppers = [x for x in self.played_by.discard_pile if x.title == "Copper"]
		if len(coppers) == 0:
			self.game.announce("-- but has no copper in their discard pile")
			crd.Card.on_finished(self, False, True)
		else:
			selection = yield self.played_by.select(1, 1, [str(i) for i in range(0, len(coppers)+1)], "Choose number of coppers to put into hand.")
			num_revealed = int(selection[0])
			added_to_hand = 0
			for i in range(len(self.played_by.discard_pile)-1, -1, -1):
				if added_to_hand == num_revealed:
					break
				elif self.played_by.discard_pile[i].title == "Copper":
					copper = self.played_by.discard_pile.pop(i)
					self.played_by.hand.add(copper)
					added_to_hand += 1
			self.played_by.update_hand()
			self.game.announce("-- removing " + str(selection[0]) + " coppers from their discard and putting them in hand.")
			self.played_by.update_discard_size()
			self.played_by.update_deck_size()
			crd.Card.on_finished(self)

class Mint(crd.Card):
	def __init__(self, game, played_by):
		crd.Card.__init__(self, game, played_by)
		self.title = "Mint"
		self.description = "You may reveal a Treasure card from your hand. Gain a copy of it.\n" \
		"When you buy this, trash all Treasures you have in play."
		self.price = 5
		self.type = "Action"

	@gen.coroutine
	def play(self, skip=False):
		crd.Card.play(self, skip)
		treasure_cards = self.played_by.hand.get_cards_by_type("Treasure", True)
		treasure_titles = list(set(map(lambda x: x.title, treasure_cards)))

		# perhaps write an auto_select method for lists?
		if len(treasure_titles) == 0:
			self.game.announce("-- but there were no treasures to reveal")
			crd.Card.on_finished(self, False, False)
		else:	
			selection = yield self.played_by.select(None, 1, treasure_titles, "Choose a card to reveal")
			if selection:
				self.game.announce("-- revealing " + self.game.log_string_from_title(selection[0]) + ", gaining a copy of it.")
				yield self.played_by.gain(selection[0])
			else:
				self.game.announce("-- revealing nothing")
			crd.Card.on_finished(self, False, False)

	def on_buy(self):
		trashed_treasures = list()
		for i in range(len(self.played_by.played_cards) - 1, -1, -1):
			if self.played_by.played_cards[i].type == 'Treasure':
				trashed_treasures.append(self.played_by.played_cards.pop(i))
		announce_string = ", ".join(list(map(lambda x: self.game.log_string_from_title(x.title), trashed_treasures)))

		self.game.announce("-- trashing " + announce_string)

		for card in trashed_treasures:
			self.game.trash_pile.append(card)

		self.game.update_trash_pile()


class Mountebank(crd.AttackCard):
	def __init__(self, game, played_by):
		crd.AttackCard.__init__(self, game, played_by)
		self.title = "Mountebank"
		self.description = "{}Each other player may discard a Curse. If they don't, they gain a Curse and a Copper.".format(crd.format_money(2))
		self.price = 5
		self.type = "Action|Attack"

	@gen.coroutine
	def play(self, skip=False):
		crd.AttackCard.play(self, skip)
		self.game.announce("-- gaining +$2")
		self.played_by.balance += 2
		self.played_by.update_resources()
		yield crd.AttackCard.check_reactions(self, self.played_by.get_opponents())

	@gen.coroutine
	def attack(self):
		yield crd.AttackCard.get_next(self, self.played_by)

	@gen.coroutine
	def fire(self, player):
		if crd.AttackCard.fire(self, player):
			if "Curse" in player.hand:
				def post_select_on(selection, player=player):
					self.post_select(selection, player)
				self.played_by.wait("to choose", player)
				selection = yield player.select(1, 1, ["Yes", "No"], "Discard a curse?")
				if selection[0] == "Yes":
					yield player.discard(["Curse"], player.discard_pile)
					curse = player.discard_pile[-1]
					self.game.announce("-- " + player.name_string() + " discards a " + curse.log_string())
					crd.AttackCard.get_next(self, player)
					return
			yield player.gain("Curse")
			yield player.gain("Copper")
			yield crd.AttackCard.get_next(self, player)

class Rabble(crd.AttackCard):
	def __init__(self, game, played_by):
		crd.AttackCard.__init__(self, game, played_by)
		self.title = "Rabble"
		self.description = "{}Each other player reveals the top 3 cards of his deck, " \
		                   "discards the revealed Actions and Treasures, and puts the rest back " \
		                   "on top in any order he chooses.".format(crd.format_draw(3))
		self.price = 5
		self.type = "Action|Attack"

	@gen.coroutine
	def play(self, skip=False):
		crd.AttackCard.play(self, skip)
		drawn = self.played_by.draw(3)
		self.game.announce("-- drawing " + drawn)
		yield crd.AttackCard.check_reactions(self, self.played_by.get_opponents())

	@gen.coroutine
	def attack(self):
		affected = [x for x in self.played_by.get_opponents() if not crd.AttackCard.is_blocked(self, x)]
		if affected:
			for player in affected:
				if len(player.deck) < 3:
					player.shuffle_discard_to_deck()

				revealed = []
				if len(player.deck) < 3:
					revealed = list(player.deck)
				else:
					revealed = player.deck[-3:]
				# removed the revealed cards from deck
				num_truncate = len(revealed)
				del player.deck[-num_truncate:]
				if len(revealed) != 0:
					self.game.announce(player.name_string() + " reveals " + ", ".join(list(map(lambda x: x.log_string(), revealed))))
				else:
					self.game.announce(player.name_string() + " reveals nothing")
				action_treasure_cards = [x for x in revealed if "Treasure" in x.type or "Action" in x.type]
				if len(action_treasure_cards) > 0:
					action_treasure_card_titles = [x.log_string() for x in action_treasure_cards]
					self.game.announce("-- discarding " + ", ".join(action_treasure_card_titles))
					yield player.discard_floating(action_treasure_cards)

				cards_left = [x for x in revealed if "Action" not in x.type and "Treasure" not in x.type]
				yield crd.reorder_top(player, cards_left)
				if not self.played_by.is_waiting():
					crd.Card.on_finished(self, False, False)
		else:
			crd.Card.on_finished(self, False, False)

class Royal_Seal(crd.Money):
	def __init__(self, game, played_by):
		crd.Money.__init__(self, game, played_by)
		self.title = "Royal Seal"
		self.description = "{}While this is in play, when you gain a card," \
		                   " you may put that card on top of your deck.".format(crd.format_money(2))
		self.price = 5
		self.value = 2
		self.spend_all = False

	@gen.coroutine
	def on_gain_effect(self, gained_card):
		selection = yield self.played_by.select(1, 1, ["Yes", "No"], "Place " + gained_card.title + " on top of deck?")
		if selection[0] == "Yes":
			gained_card = self.played_by.search_and_extract_card(gained_card)
			self.game.announce(self.played_by.name_string() + " uses " + self.log_string() + " to place "
				+ gained_card.log_string() + " on the top of their deck")
			self.played_by.deck.append(gained_card)

class Vault(crd.Card):
	def __init__(self, game, played_by):
		crd.Card.__init__(self, game, played_by)
		self.title = "Vault"
		self.description = "{}Discard any number of cards. +$1 per card discarded. " \
		                   "Each other player may discard 2 cards. If he does, he draws a card.".format(crd.format_draw(2))
		self.price = 5
		self.type = "Action"

	@gen.coroutine
	def play(self, skip=False):
		crd.Card.play(self, skip)
		drawn = self.played_by.draw(2)
		self.game.announce("-- drawing " + drawn)

		selection = yield self.played_by.select(None, len(self.played_by.hand.card_array()),
		                      crd.card_list_to_titles(self.played_by.hand.card_array()), "Discard any number of cards")
		yield self.played_by.discard(selection, self.played_by.discard_pile)
		self.played_by.balance += len(selection)
		self.game.announce("-- discarding " + str(len(selection)) +
		                   ", gaining +$" + str(len(selection)))

		self.played_by.wait_many("to discard", self.played_by.get_opponents(), True)
		#ask opponents to discard 2 to draw 1
		opponents = self.played_by.get_opponents()
		yield crd.parallel_selects(map(lambda x: x.select(1, 1, ["Yes", "No"], "Discard 2 cards to draw 1?"), 
			opponents), opponents, self.discard_2_for_1)

	@gen.coroutine
	def discard_2_for_1(self, selection, player):
		if selection[0] == "Yes":
			discard_selection = yield player.select(min(len(player.hand.card_array()), 2), 2, crd.card_list_to_titles(player.hand.card_array()), "Discard up to 2")
			yield player.discard(discard_selection, player.discard_pile)
			drawn = "nothing"
			if len(discard_selection) >= 2:
				drawn = player.draw(1)
			self.game.announce(player.name_string() + " discards " + str(len(discard_selection)) + " cards and draws " + drawn)
		player.update_wait(True)
		if not self.played_by.is_waiting():
			self.played_by.update_mode()
			crd.Card.on_finished(self, False, True)

class Venture(crd.Money):
	def __init__(self, game, played_by):
		crd.Money.__init__(self, game, played_by)
		self.title = "Venture"
		self.description = "{}When you play this, reveal cards from your deck until you reveal a Treasure. " \
		                   "Discard the other cards. Play that Treasure.".format(crd.format_money(1))
		self.price = 5
		self.value = 1
		self.type = "Treasure"
		self.spend_all = False

	@gen.coroutine
	def play(self, skip=False):
		crd.Card.play(self, skip)
		self.played_by.balance += self.value
		self.played_by.update_resources(True)

		found_card = yield crd.search_deck_for(self.played_by, lambda x : "Treasure" in x.type)
		if found_card is None:
			self.game.announce("-- but could not find any treasures in his or her deck.")
		else:
			self.game.announce("-- revealing " + found_card.log_string())
			self.game.announce("-- " + self.played_by.name_string() + " played " + found_card.log_string())
			self.played_by.played_cards.append(found_card)
			yield gen.maybe_future(found_card.play(True))
		crd.Money.on_finished(self)

# --------------------------------------------------------
# ------------------------ 6 Cost ------------------------
# --------------------------------------------------------


class Goons(crd.AttackCard):
	def __init__(self, game, played_by):
		crd.AttackCard.__init__(self, game, played_by)
		self.title = "Goons"
		self.description = "{}{}Each other player discards down to 3 cards in hand." \
		                   "\nWhile this is in play, when you buy a card, +1 VP token.".format(crd.format_buys(1), crd.format_money(2))
		self.price = 6
		self.type = "Action|Attack"

	@gen.coroutine
	def play(self, skip=False):
		crd.AttackCard.play(self, skip)
		self.played_by.balance += 2
		self.played_by.buys += 1

		self.game.announce("-- gaining +$2 and +1 Buy")
		self.played_by.update_resources()
		yield crd.AttackCard.check_reactions(self, self.played_by.get_opponents())

	@gen.coroutine
	def attack(self):
		affected = [x for x in self.played_by.get_opponents() if not crd.AttackCard.is_blocked(self, x)]
		if affected:
			yield crd.discard_down(affected, 3)
		crd.Card.on_finished(self, False, False)
		
	def on_buy_effect(self, purchased_card):
		self.played_by.vp += 1
		self.game.announce("-- gaining +1 VP")

	def log_string(self, plural=False):
		return "".join(["<span class='label label-attack'>", self.title, "</span>"])

class Hoard(crd.Money):
	def __init__(self, game, played_by):
		crd.Card.__init__(self, game, played_by)
		self.title = "Hoard"
		self.description = "{}While this is in play, when you buy a Victory card, gain a Gold.".format(crd.format_money(2))
		self.price = 6
		self.value = 2
		self.type = "Treasure"
		self.spend_all = False

	@gen.coroutine
	def on_buy_effect(self, purchased_card):
		if "Victory" in purchased_card.type:
			yield self.played_by.gain("Gold", True, "-- gaining a " + self.played_by.get_card_from_supply("Gold", False).log_string()) 

class Grand_Market(crd.Card):
	def __init__(self, game, played_by):
		crd.AttackCard.__init__(self, game, played_by)
		self.title = "Grand Market"
		self.description = "{}{}{}{}You can't buy this card if you have copper in play".format(crd.format_draw(1), 
			crd.format_actions(1), crd.format_buys(1), crd.format_money(2))
		self.price = 6
		self.type = "Action"

	def play(self, skip=False):
		crd.Card.play(self, skip)
		drawn = self.played_by.draw(1)
		self.played_by.actions += 1
		self.played_by.balance += 2
		self.played_by.buys += 1
		self.game.announce("-- drawing " + drawn + " , gaining +1 action, +1 buy and $2")
		crd.Card.on_finished(self)

# --------------------------------------------------------
# ------------------------ 7 Cost ------------------------
# --------------------------------------------------------


class Bank(crd.Money):
	def __init__(self, game, played_by):
		crd.Money.__init__(self, game, played_by)
		self.title = "Bank"
		self.description = "{}When you play this, it’s worth $1 per Treasure card you have in play (counting this).".format(crd.format_money("X"))
		self.price = 7
		self.value = 0
		self.type = "Treasure"
		self.spend_all = False

	def play(self, skip=False):
		crd.Card.play(self, skip)
		total_played_treasures = 0
		for card in self.played_by.played_cards:
			if "Treasure" in card.type:
				total_played_treasures += 1
		self.played_by.balance += total_played_treasures
		self.game.announce("-- gaining +$" + str(total_played_treasures))
		crd.Card.on_finished(self)


class Expand(crd.Card):
	def __init__(self, game, played_by):
		crd.Card.__init__(self, game, played_by)
		self.title = "Expand"
		self.description = "Trash a card from your hand. Gain a card costing up to $3 more than the trashed card."
		self.price = 7
		self.type = "Action"

	@gen.coroutine
	def play(self, skip=False):
		crd.Card.play(self, skip)
		selection = yield self.played_by.select(1, 1, crd.card_list_to_titles(self.played_by.hand.card_array()),
		                      "select card to expand")
		if selection:
			yield self.played_by.discard(selection, self.game.trash_pile)
			card_trashed = self.game.card_from_title(selection[0])
			self.game.announce(self.played_by.name_string() + " trashes " + card_trashed.log_string())
			selected = yield self.played_by.select_from_supply("Choose the expanded card", lambda x : x.get_price() <= card_trashed.get_price() + 3)
			if selected:
				yield self.played_by.gain(selected[0])
				crd.Card.on_finished(self, False, False)
		else:
			self.game.announce("-- but has nothing to expand.")
			self.played_by.update_resources()

class Kings_Court(crd.Card):
	def __init__(self, game, played_by):
		crd.Card.__init__(self, game, played_by)
		self.title = "King's Court"
		self.description = "Choose an action card from your hand. Play it three times."
		self.price = 7
		self.type = "Action"

	@gen.coroutine
	def play(self, skip=False):
		crd.Card.play(self, skip)
		action_cards = self.played_by.hand.get_cards_by_type("Action")
		selection = yield self.played_by.select(1, 1, crd.card_list_to_titles(action_cards),
		 "select card for King's Court")
		if not selection:
			self.game.announce(" -- but has no action cards")
			crd.Card.on_finished(self, False, False)
		else:
			selected_card = self.played_by.hand.extract(selection[0])
			kings_court_str = self.played_by.name_string() + " " + self.log_string(True) + " " + selected_card.log_string()
			if "Duration" in selected_card.type:
				if self not in self.played_by.durations:
					self.played_by.played_cards.pop()
					self.played_by.durations.append(self)
				self.played_by.durations.append(selected_card)
				self.played_by.duration_cbs.append(lambda x=selected_card : self.active_duration(x))
				self.game.update_duration_mat()
			else:
				self.played_by.played_cards.append(selected_card)
			for i in range(0, 3):
				self.game.announce(kings_court_str)
				yield gen.maybe_future(selected_card.play(True))
				self.played_by.update_resources()
				self.played_by.update_hand()
			crd.Card.on_finished(self, False, False)

	@gen.coroutine
	def active_duration(self, selected_duration):
		kings_court_str = "{} resolves {}".format(self.log_string(), selected_duration.log_string())
		self.game.announce(kings_court_str)
		for i in range(0, 3):
			d = self.played_by.duration_cbs.popleft()
			yield gen.maybe_future(d())

class Forge(crd.Card):
	def __init__(self, game, played_by):
		crd.Card.__init__(self, game, played_by)
		self.title = "Forge"
		self.description = "Trash any number of cards from your hand. " \
		                   "Gain a card with cost exactly equal to the total cost in coins of the trashed cards."
		self.price = 7
		self.type = "Action"

	@gen.coroutine
	def play(self, skip=False):
		crd.Card.play(self, skip)
		self.played_by.wait_modeless("", self.played_by, True)
		forge_selection = yield self.played_by.select(None, len(self.played_by.hand.card_array()), 
			crd.card_list_to_titles(self.played_by.hand.card_array()), "Trash any number of cards")
		trash_sum = 0
		if forge_selection:
			for card in forge_selection:
				trash_card = self.played_by.hand.extract(card)
				trash_sum += trash_card.get_price()
				self.game.trash_pile.append(trash_card)
			announce_string = list(map(lambda x: self.game.card_from_title(x).log_string(), forge_selection))
			self.game.announce(self.played_by.name_string() + " trashes " + ", ".join(announce_string) + " to gain a card with cost " + str(trash_sum))
		else:
			self.game.announce("{} trashes nothing to gain a card with cost 0".format(self.played_by.name_string()))
		self.game.update_trash_pile()

		gained = yield self.played_by.select_from_supply("Gain a card from the forge", lambda x : x.get_price() == trash_sum, optional=False)
		if gained:
			yield self.played_by.gain(gained[0])
		self.played_by.update_wait(True)
		crd.Card.on_finished(self)

# --------------------------------------------------------
# ------------------------ 8 Cost ------------------------
# --------------------------------------------------------

class Peddler(crd.Card):
	def __init__(self, game, played_by):
		crd.Card.__init__(self, game, played_by)
		self.title = "Peddler"
		self.description = "{}{}{}During your Buy phase, "\
			"this costs $2 less for each action card in play (not less than $0)".format(crd.format_draw(1), crd.format_actions(1), crd.format_money(1))
		self.price = 8
		self.type = "Action"

	def play(self, skip=False):
		crd.Card.play(self, skip)
		self.played_by.balance += 1
		drawn = self.played_by.draw(1)
		self.game.announce("-- drawing " + drawn + " gaining $1 and 1 action")
		self.played_by.actions += 1
		crd.Card.on_finished(self)

	#called when the buy phase begins
	def on_buy_phase(self):
		modifier = len([x for x in self.game.get_turn_owner().played_inclusive if "Action" in x.type]) * -2
		self.game.price_modifier[self.title] += modifier
