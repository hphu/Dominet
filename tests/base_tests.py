import unittest
import client as c
import sets.base as base
import sets.intrigue as intrigue
import sets.prosperity as prosperity
import sets.card as crd
import game as g
import kingdomGenerator as kg

import tests.test_utils as tu

class TestCard(unittest.TestCase):
	def setUp(self):
		self.player1 = c.DmClient("player1", 0, tu.PlayerHandler())
		self.player2 = c.DmClient("player2", 1, tu.PlayerHandler())
		self.player3 = c.DmClient("player3", 2, tu.PlayerHandler())
		self.game = g.DmGame([self.player1, self.player2, self.player3], kg.all_card_titles(), [])
		self.game.players = [self.player1, self.player2, self.player3]
		for i in self.game.players:
			i.game = self.game
		self.game.start_game()
		self.player1.take_turn()

	# --------------------------------------------------------
	# ------------------------- Base -------------------------
	# --------------------------------------------------------

	def test_Cellar(self):
		tu.print_test_header("test Cellar")

		self.player1.hand.add(base.Cellar(self.game, self.player1))
		self.player1.hand.play("Cellar")
		self.assertTrue(self.player1.handler.log[-1]["command"] == "updateMode")
		self.assertTrue(self.player1.handler.log[-1]["mode"] == "select")
		self.assertTrue(self.player1.cb != None)

		selection = crd.card_list_to_titles(self.player1.hand.card_array())
		tu.send_input(self.player1, "post_selection", selection)
		self.assertTrue(len(self.player1.discard_pile) == 5)

	def test_Militia(self):
		tu.print_test_header("test Militia")
		self.player1.hand.add(base.Militia(self.game, self.player1))
		self.player1.hand.play("Militia")
		self.assertTrue(self.player2.handler.log[-1]["command"] == "updateMode")
		self.assertTrue(self.player2.handler.log[-1]["mode"] == "select")
		self.assertTrue(self.player2.handler.log[-1]["select_from"] == crd.card_list_to_titles(self.player2.hand.card_array()))
		self.assertTrue(self.player2.cb != None)

		selection = crd.card_list_to_titles(self.player2.hand.card_array())[:2]
		tu.send_input(self.player2, "post_selection", selection)
		self.assertTrue(len(self.player2.hand) == 3)

	def test_Moat_reaction(self):
		tu.print_test_header("test Moat Reaction")
		self.player2.hand.add(base.Moat(self.game, self.player2))
		self.player1.hand.add(base.Witch(self.game, self.player1))
		self.player1.hand.play("Witch")
		self.assertTrue("Reveal" in self.player2.handler.log[-1]["select_from"])

		tu.send_input(self.player2, "post_selection", ["Reveal"])
		# didn't gain curse
		self.assertTrue(len(self.player2.discard_pile) == 0)

	def test_Throne_Room_on_Village(self):
		tu.print_test_header("test Throne Room Village")
		throne_room_card = base.Throne_Room(self.game, self.player1)
		self.player1.hand.add(throne_room_card)
		self.player1.hand.add(base.Village(self.game, self.player1))
		throne_room_card.play()
		throne_room_card.post_select(["Village"])
		self.assertTrue(self.player1.actions == 4)

	def test_Throne_Room_on_Workshop(self):
		tu.print_test_header("test Throne Room workshop")
		throne_room_card = base.Throne_Room(self.game, self.player1)
		self.player1.hand.add(throne_room_card)
		workshopCard = base.Workshop(self.game, self.player1)
		self.player1.hand.add(workshopCard)
		throne_room_card.play()
		throne_room_card.post_select(["Workshop"])
		self.assertTrue(workshopCard.done.__name__ == "second_play")

		tu.send_input(self.player1, "selectSupply", ["Silver"])
		self.assertTrue(self.player1.discard_pile[-1].title == "Silver")
		self.assertTrue(workshopCard.done.__name__ == "final_done")

		tu.send_input(self.player1, "selectSupply", ["Estate"])
		self.assertTrue(self.player1.discard_pile[-1].title == "Estate")

	def test_Feast(self):
		tu.print_test_header("test Feast")
		feast_card = base.Feast(self.game, self.player1)
		self.player1.hand.add(feast_card)
		feast_card.play()

		self.assertTrue(self.player1.handler.log[-1]["mode"] == "selectSupply")
		self.assertTrue(self.game.trash_pile[-1] == feast_card)

	def test_Thief_2_treasures(self):
		tu.print_test_header("test Thief on 2 treasures")
		thief_card = base.Thief(self.game, self.player1)
		self.player1.hand.add(thief_card)
		self.player2.deck.append(crd.Copper(self.game, self.player2))
		self.player2.deck.append(crd.Silver(self.game, self.player2))
		thief_card.play()
		self.assertTrue("Copper" in self.player1.handler.log[-1]['select_from'])
		self.assertTrue("Silver" in self.player1.handler.log[-1]['select_from'])
		tu.send_input(self.player1, "post_selection", ["Silver"])
		self.assertTrue(self.game.trash_pile[-1].title == "Silver")
		tu.send_input(self.player1, "post_selection", ["Yes"])
		self.assertTrue(self.player1.discard_pile[-1].title == "Silver")

	def test_Thief_1_treasure(self):
		tu.print_test_header("test Thief on 1 treasure")
		thief_card = base.Thief(self.game, self.player1)
		self.player1.hand.add(thief_card)
		self.player2.deck.append(crd.Estate(self.game, self.player2))
		self.player2.deck.append(crd.Gold(self.game, self.player2))
		thief_card.play()
		self.assertTrue(self.game.trash_pile[-1].title == "Gold")
		tu.send_input(self.player1, "post_selection", ["Yes"])
		self.assertTrue(self.player1.discard_pile[-1].title == "Gold")

	def test_Thief_3_players(self):
		tu.print_test_header("test Thief 3 players")
		thief_card = base.Thief(self.game, self.player1)
		self.player1.hand.add(thief_card)
		self.player2.deck.append(crd.Estate(self.game, self.player2))
		self.player2.deck.append(crd.Gold(self.game, self.player2))
		self.player3.deck.append(crd.Copper(self.game, self.player2))
		self.player3.deck.append(crd.Estate(self.game, self.player2))
		thief_card.play()
		tu.send_input(self.player1, "post_selection", ["Yes"])
		self.assertTrue(self.player1.discard_pile[-1].title == "Gold")
		tu.send_input(self.player1, "post_selection", ["Yes"])
		self.assertTrue(self.player1.discard_pile[-1].title == "Copper")
		thief_card.play()


	def test_Gardens(self):
		tu.print_test_header("test Gardens")
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
		tu.print_test_header("test Chancellor")
		self.player1.discard_pile.append(crd.Copper(self.game, self.player1))
		chancellor = base.Chancellor(self.game, self.player1)
		self.player1.hand.add(chancellor)
		chancellor.play()
		self.assertTrue(self.player1.handler.log[-1]["command"] == "updateMode")
		self.assertTrue(len(self.player1.discard_pile) == 1)
		decksize = len(self.player1.deck)
		tu.send_input(self.player1, "post_selection", ["Yes"])

		self.assertTrue(len(self.player1.discard_pile) == decksize + 1)
		self.assertTrue(len(self.player1.deck) == 0)

	def test_Adventurer(self):
		tu.print_test_header("test Adventurer")
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

	def test_Adventurer_empty_deck(self):
		tu.print_test_header("test Adventurer")
		estate = crd.Estate(self.game, self.player1)
		gold = crd.Gold(self.game, self.player1)
		adventurer = base.Adventurer(self.game, self.player1)
		self.player1.deck = []
		self.player1.discard_pile = [gold]

		self.player1.hand.add(adventurer)
		adventurer.play()
		self.assertTrue(self.player1.hand.get_count("Gold") == 1)
		self.assertTrue(len(self.player1.deck) == 0)
		self.assertTrue(len(self.player1.discard_pile) == 0)

	def test_Library(self):
		tu.print_test_header("test Library")
		library = base.Library(self.game, self.player1)
		village = base.Village(self.game, self.player1)
		copper = crd.Copper(self.game, self.player1)
		self.player1.deck = [copper, village, copper]
		self.player1.hand.add(library)
		library.play()
		self.assertTrue(len(self.player1.hand) == 6)
		self.assertTrue(self.player1.handler.log[-1]["command"] == "updateMode")
		tu.send_input(self.player1, "post_selection", ["Yes"])
		self.assertTrue(len(self.player1.hand) == 7)
		self.assertTrue(self.player1.discard_pile[-1] == village)

	def test_Witch(self):
		tu.print_test_header("test Witch")
		witch = base.Witch(self.game, self.player1)
		witch.play()
		self.assertTrue(self.player2.discard_pile[-1].title == "Curse")
		self.assertTrue(self.player3.discard_pile[-1].title == "Curse")
		self.assertTrue(self.player1.last_mode["mode"] != "wait")

	def test_2_Reactions(self):
		tu.print_test_header("test 2 reaction secret chamber moat")
		militia = base.Militia(self.game, self.player1)
		moat = base.Moat(self.game, self.player2)
		secret_chamber = intrigue.Secret_Chamber(self.game, self.player2)
		estate = crd.Estate(self.game, self.player2)
		self.player2.hand.add(moat)
		self.player2.hand.add(secret_chamber)
		self.player2.deck.append(estate)
		self.player2.deck.append(estate)
		moat3 = base.Moat(self.game, self.player3)
		secret_chamber3 = intrigue.Secret_Chamber(self.game, self.player3)
		silver = crd.Silver(self.game, self.player3)
		self.player3.hand.data = {"Silver": [silver, silver, silver]}
		self.player3.hand.add(moat3)
		self.player3.hand.add(secret_chamber3)
		

		militia.play()
		self.assertTrue(self.player1.last_mode["mode"] == "wait")
		self.assertTrue(self.player2.last_mode["mode"] == "select")
		self.assertTrue("Secret Chamber" in self.player2.last_mode["select_from"])		
		self.assertTrue("Moat" in self.player2.last_mode["select_from"])
		self.player2.exec_commands({"command":"post_selection", "selection":["Secret Chamber", "Moat"]})
		#moat trigger first
		self.assertTrue("Moat" in self.player2.last_mode["msg"])
		self.assertTrue(self.player1.last_mode["mode"] == "wait")

		#while player2 is deciding to reveal moat or not,
		#player3 chose order Secret chamber first
		self.assertTrue(self.player3.last_mode["mode"] == "select")
		self.player3.exec_commands({"command":"post_selection", "selection":["Moat", "Secret Chamber"]})
		self.assertTrue(self.player1.last_mode["mode"] == "wait")
		self.assertTrue("Secret Chamber" in self.player3.last_mode["msg"])
		self.player3.exec_commands({"command":"post_selection", "selection": ["Reveal"]})
		#player3 chooses to put back secret chamber and moat in secret chamber reaction 
		self.player3.exec_commands({"command":"post_selection", "selection": ["Secret Chamber", "Moat"]})
		self.assertTrue(self.player3.deck[-1].title == "Moat")
		self.assertTrue(self.player3.deck[-2].title == "Secret Chamber")
		self.assertTrue(self.player1.last_mode["mode"] == "wait")
		#player2 reveals moat
		self.assertTrue(self.player2.last_mode["mode"] == "select")
		self.player2.exec_commands({"command":"post_selection", "selection": ["Reveal"]})
		self.assertTrue(self.player1.last_mode["mode"] == "wait")
		#player2 reveals secret chamber
		self.player2.exec_commands({"command":"post_selection", "selection": ["Reveal"]})
		#player2 puts back Estate, moat
		self.assertTrue(self.player2.protection == 1)
		self.assertTrue(self.player1.last_mode["mode"] == "wait")
		self.player2.exec_commands({"command":"post_selection", "selection": ["Moat", "Estate"]})
		self.assertTrue(self.player2.deck[-1].title == "Estate")
		self.assertTrue(self.player2.deck[-2].title == "Moat")

		
		#player3 discards 2 silver
		self.player3.exec_commands({"command":"post_selection", "selection": ["Silver", "Silver"]})

		self.assertTrue(len(self.player3.hand)==3)
		#player1 resumes
		self.assertTrue(self.player1.last_mode["mode"] == "buy")


if __name__ == '__main__':
	unittest.main()