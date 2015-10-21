from tornado import ioloop, gen

class WaitHandler():
	def __init__(self, player):
		self.player = player
		# on = list of player names waiting for, callback called after select/gain gets response, 
		self.waiting_on = []
		self.msg = ""
		#locked = set of player names we ignore auto updates (and keep waiting) until manually removed from locked set
		self.locked = set()
		self.afk_timer = None
		self.is_afk = False

	def wait(self, msg):
		self.msg = msg
		self.remove_afk_timer()
		for i in self.waiting_on:
			self.player.game.get_player_from_name(i).waiter.time_afk()
		self.player.write_json(command="updateMode", mode="wait", msg="Waiting for " + self.waiting_on_string() + " " + self.msg)

	def append_wait(self, to_append):
		if not self.is_waiting_on(to_append):
			self.waiting_on.append(to_append.name)

	def notify(self, notifier):
		if not notifier.name in self.locked:
			if self.is_waiting_on(notifier):
				self.waiting_on.remove(notifier.name)
				notifier.waiter.remove_afk_timer()
				if not self.is_waiting():
					self.player.update_mode()
					self.time_afk()
				elif not self.is_waiting_on(self.player):
					self.wait(self.msg)

	def set_lock(self, locked_person, locked):
		if locked:
			self.locked.add(locked_person.name)
		elif locked_person.name in self.locked:
			self.locked.remove(locked_person.name)

	def waiting_on_string(self):
		return ", ".join(self.waiting_on)

	def is_waiting_on(self, player):
		return player.name in self.waiting_on

	def is_waiting(self):
		return len(self.waiting_on) > 0

	@gen.coroutine
	def time_afk(self):
		@gen.coroutine
		def afk_cb():
			self.is_afk = True
			afk_players = [x for x in self.player.game.players if x.waiter.is_afk]
			futures = []
			for i in self.player.get_opponents():
				if i not in afk_players:
					futures.append(i.select(1,1, ["Yes"],
						"{} {} not responded for over 5 minutes, force forefeit?".format(", ".join([i.name for i in afk_players]), "have" if len(afk_players) > 1 else "has")))	
					wait_iterator = gen.WaitIterator(*futures)
			while not wait_iterator.done():
				selected = yield wait_iterator.next()
				if selected == ["Yes"]:
					self.player.game.end_game([afk_players])
		self.afk_timer = ioloop.IOLoop.instance().call_later(360, afk_cb)

	def reset_afk_timer(self):
		self.remove_afk_timer()
		self.time_afk()

	def remove_afk_timer(self):
		if self.afk_timer:
			ioloop.IOLoop.instance().remove_timeout(self.afk_timer)
			self.afk_timer = None
			self.is_afk = False
			for i in self.player.get_opponents():
				i.write_json(**i.last_mode)


