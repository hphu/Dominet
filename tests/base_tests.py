import unittest
import client as c
import base_set as base
import intrigue_set as intrigue
import card as crd
import game as g
import kingdomGenerator as kg


class Player1Handler():
	log = []

	def write_json(self, **kwargs):
		if kwargs["command"] != "announce":
			Player1Handler.log.append(kwargs)


class Player2Handler():
	log = []

	def write_json(self, **kwargs):
		if kwargs["command"] != "announce":
			Player2Handler.log.append(kwargs)

class TestCard(unittest.TestCase):
	def setUp(self):
		self.player1 = c.DmClient("player1", 0, Player1Handler())
		self.player2 = c.DmClient("player2", 1, Player2Handler())
		self.game = g.DmGame([self.player1, self.player2], [])
		self.game.supply = self.game.init_supply(kg.all_cards(self.game))
		for i in self.game.players:
			i.game = self.game
			i.setup()
		self.player1.take_turn()
		Player1Handler.log = []
		Player2Handler.log = []

	# --------------------------------------------------------
	# ------------------------- Base -------------------------
	# --------------------------------------------------------

	def test_Cellar(self):
		self.player1.hand.add(base.Cellar(self.game, self.player1))
		self.player1.hand.play("Cellar")
		self.assertTrue(Player1Handler.log[0]["command"] == "updateMode")
		self.assertTrue(Player1Handler.log[0]["mode"] == "select")
		self.assertTrue(self.player1.waiting["cb"] != None)

		selection = crd.card_list_to_titles(self.player1.hand.card_array())
		self.player1.waiting["cb"](selection)
		self.assertTrue(len(self.player1.discard_pile) == 5)

	def test_Militia(self):
		self.player1.hand.add(base.Militia(self.game, self.player1))
		self.player1.hand.play("Militia")
		self.assertTrue(Player2Handler.log[0]["command"] == "updateMode")
		self.assertTrue(Player2Handler.log[0]["mode"] == "select")
		self.assertTrue(Player2Handler.log[0]["select_from"] == crd.card_list_to_titles(self.player2.hand.card_array()))
		self.assertTrue(self.player2.waiting["cb"] != None)

		selection = crd.card_list_to_titles(self.player2.hand.card_array())[:2]
		self.player2.waiting["cb"](selection)
		self.assertTrue(len(self.player2.hand) == 3)

	def test_Moat_reaction(self):
		self.player2.hand.add(base.Moat(self.game, self.player2))
		self.player1.hand.add(base.Witch(self.game, self.player1))
		self.player1.hand.play("Witch")
		self.assertTrue("Reveal" in Player2Handler.log[0]["select_from"])
		self.player2.waiting["cb"](["Reveal"])
		# didn't gain curse
		self.assertTrue(len(self.player2.discard_pile) == 0)

	def test_Throne_Room_on_Village(self):
		throne_room_card = base.Throne_Room(self.game, self.player1)
		self.player1.hand.add(throne_room_card)
		self.player1.hand.add(base.Village(self.game, self.player1))
		throne_room_card.play()
		self.assertTrue(Player1Handler.log[0]["select_from"] == ["Village"])
		throne_room_card.post_select(["Village"])
		self.assertTrue(self.player1.actions == 4)

	def test_Throne_Room_on_Workshop(self):
		throne_room_card = base.Throne_Room(self.game, self.player1)
		self.player1.hand.add(throne_room_card)
		workshopCard = base.Workshop(self.game, self.player1)
		self.player1.hand.add(workshopCard)
		throne_room_card.play()
		throne_room_card.post_select(["Workshop"])
		self.assertTrue(workshopCard.done.__name__ == "second_play")

		self.player1.update_wait()
		self.player1.waiting["cb"]("Silver")
		self.assertTrue(self.player1.discard_pile[-1].title == "Silver")
		self.assertTrue(workshopCard.done.__name__ == "final_done")

		self.player1.update_wait()
		self.player1.waiting["cb"]("Estate")
		self.assertTrue(self.player1.discard_pile[-1].title == "Estate")

	def test_Feast(self):
		feast_card = base.Feast(self.game, self.player1)
		self.player1.hand.add(feast_card)
		feast_card.play()

		self.assertTrue(Player1Handler.log[-1]["mode"] == "selectSupply")
		self.assertTrue(self.game.trash_pile[-1] == feast_card)

	def test_Thief_2_treasures(self):
		thief_card = base.Thief(self.game, self.player1)
		self.player1.hand.add(thief_card)
		self.player2.deck.append(crd.Copper(self.game, self.player2))
		self.player2.deck.append(crd.Silver(self.game, self.player2))
		thief_card.play()
		self.assertTrue("Copper" in Player1Handler.log[-1]['select_from'])
		self.assertTrue("Silver" in Player1Handler.log[-1]['select_from'])
		self.player1.waiting["cb"](["Silver"])
		self.assertTrue(self.game.trash_pile[-1].title == "Silver")
		self.player1.waiting["cb"](["Yes"])
		self.assertTrue(self.player1.discard_pile[-1].title == "Silver")

	def test_Thief_1_treasure(self):
		thief_card = base.Thief(self.game, self.player1)
		self.player1.hand.add(thief_card)
		self.player2.deck.append(crd.Estate(self.game, self.player2))
		self.player2.deck.append(crd.Gold(self.game, self.player2))
		thief_card.play()
		self.assertTrue(self.game.trash_pile[-1].title == "Gold")
		self.player1.waiting["cb"](["Yes"])
		self.assertTrue(self.player1.discard_pile[-1].title == "Gold")

	def test_Gardens(self):
		gardens = base.Gardens(self.game, self.player1)
		self.player1.hand.add(gardens)
		self.assertTrue(gardens.get_vp() == 1)
		for i in range(0, 9):
			self.player1.deck.append(base.Gardens(self.game, self.player1))
		# decksize = 20
		self.assertTrue(self.player1.total_vp() == 23)
		self.player1.deck.append(crd.Copper(self.game, self.player1))
		self.assertTrue(self.player1.total_vp() == 23)

	def test_Chancellor(self):
		self.player1.discard_pile.append(crd.Copper(self.game, self.player1))
		chancellor = base.Chancellor(self.game, self.player1)
		self.player1.hand.add(chancellor)
		chancellor.play()
		self.assertTrue(Player1Handler.log[-1]["command"] == "updateMode")
		self.assertTrue(len(self.player1.discard_pile) == 1)
		decksize = len(self.player1.deck)
		self.player1.waiting["cb"](["Yes"])
		self.assertTrue(len(self.player1.discard_pile) == 0)
		self.assertTrue(len(self.player1.deck) == decksize + 1)

	def test_Adventurer(self):
		estate = crd.Estate(self.game, self.player1)
		gold = crd.Gold(self.game, self.player1)
		adventurer = base.Adventurer(self.game, self.player1)
		self.player1.deck = [estate, estate, estate]
		self.player1.discard_pile = [gold, gold]

		self.player1.hand.add(adventurer)
		adventurer.play()
		self.assertTrue(self.player1.hand.get_count("Gold") == 2)
		self.assertTrue(len(self.player1.deck) == 0)
		self.assertTrue(len(self.player1.discard_pile) == 3)

	def test_Library(self):
		library = base.Library(self.game, self.player1)
		village = base.Village(self.game, self.player1)
		copper = crd.Copper(self.game, self.player1)
		self.player1.deck = [copper, village, copper]
		self.player1.hand.add(library)
		library.play()
		self.assertTrue(len(self.player1.hand) == 6)
		self.assertTrue(Player1Handler.log[-1]["command"] == "updateMode")
		self.player1.waiting["cb"]("Yes")
		self.assertTrue(len(self.player1.hand) == 7)
		self.assertTrue(self.player1.discard_pile[-1] == village)

	def test_Pawn(self):
		pawn = intrigue.Pawn(self.game, self.player1)
		self.player1.hand.add(pawn)
		pawn.play()
		self.player1.waiting["cb"](["+$1", "+1 Action"])
		self.assertTrue(self.player1.balance == 1)
		self.assertTrue(self.player1.actions == 1)

	def test_Great_Hall(self):
		great_hall = intrigue.Great_Hall(self.game, self.player1)
		player1_vp = self.player1.total_vp()
		self.player1.hand.add(great_hall)
		great_hall.play()
		self.assertTrue((self.player1.actions == 1))
		self.assertTrue((self.player1.total_vp()) == player1_vp + 1)

	def test_Steward(self):
		steward = intrigue.Steward(self.game, self.player1)
		copper = crd.Copper(self.game, self.player1)
		estate = crd.Estate(self.game, self.player1)
		self.player1.hand.data = {
			"Steward": [steward, 3],
			"Copper": [copper, 3],
			"Estate": [estate, 2]
		}

		self.player1.actions = 5

		# +$2
		steward.play()
		self.player1.waiting["cb"](["+$2"])
		self.assertTrue(self.player1.balance == 2)

		# Trash 2 with more than 2 in hand
		steward.play()
		trash_size = len(self.game.trash_pile)
		self.player1.waiting["cb"](["Trash 2 cards from hand"])
		self.player1.waiting["cb"](["Estate", "Estate"])
		self.assertTrue(len(self.game.trash_pile) == trash_size + 2)

		# Trash 2 with homogeneous hand
		steward.play()
		self.player1.waiting["cb"](["Trash 2 cards from hand"])
		self.assertTrue(self.player1.hand.get_count("Copper") == 1)

		self.player1.hand.add(steward, 1)

		# Trash 2 with 1 in hand
		self.player1.hand.data["Steward"] = [steward, 1]
		steward.play()
		self.player1.waiting["cb"](["Trash 2 cards from hand"])
		self.assertTrue(len(self.player1.hand) == 0)

if __name__ == '__main__':
	unittest.main()