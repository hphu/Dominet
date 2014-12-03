import socket
import threading
import http.server
import socketserver
import client

HOST = ''
PORT_NUMBER = 9999
ROOT = "/"
INDEX = "index.html"
NUM_PLAYERS = 2


class myHandler(http.server.BaseHTTPRequestHandler):
	def do_GET(self):
		#mimetypes doesn't need to be global since its only used for get requests
		mimetypes = { "css": "text/css", 
			 "html": "text/html", 
		   "js": "text/javascript"}

		print("\033[94m GET request for: " + self.path + "\033[0m")

		if self.path.startswith("/wait/"):
			id = int(self.path.split("/")[-1])
			p = self.getClient(id)

			if not p:
				self.send_error(404, "ERROR no client with id " + str(id))
			else:
				item = p.getAction()
				self.send_response(200)
				self.end_headers()
				self.wfile.write(item)
			return

		#serve static files
		resource = self.__routesHelper(self.path)
		try:
			f = open(resource, "rb")
			data = f.read()
			self.send_response(200)
			self.send_header("Content-type", mimetypes.get(resource.split(".")[1], "text/plain"))
			self.end_headers()
			self.wfile.write(data)
			f.close()
		except:
			print ("404 not found {0}".format(resource))
			self.send_error(404, "ERROR")
		
	def __routesHelper(self, request):
		#File requests 
		if (request.startswith("/")):
			if request == ROOT:
				return INDEX
			else:
				f = request[1:]
				return f

	def do_POST(self):
		print("POST request for: " + self.path)

		#initialize new client
		if self.path=="/":
			with self.server.serverLock:
				id = self.server.unassigned_id
				self.server.unassigned_id += 1
			c = client.DmClient(id)
			self.send_response(200)
			self.send_header("Content-type", "text/plain")
			self.end_headers()
			self.wfile.write(str(id).encode())

		elif self.path.startswith("/respond/"):
			id = int(self.path.split("/")[-1])
			p = self.getClient(id)

			if not p:
				self.send_error(404, "ERROR no client with id " + str(id))
			else:
				length = int(self.headers["Content-length"])
				data = self.rfile.read(length)
				p.PostResponse(data)
				self.send_response(200)
				self.end_headers()

	def getClient(self, id):
		with client.Client.clientLock:
			currentClient = client.Client.idMap.get(id)
		return currentClient

class asyncHttpServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
  #terminate all spawned threads on exit
  daemon_threads = True
  reuse_address = True
  unassigned_id = 1
  serverLock = threading.Lock()

def start_server():
	server = asyncHttpServer((HOST, PORT_NUMBER), myHandler)
	print("Server started on " + str(PORT_NUMBER))	
	server.serve_forever()

def start_game(players):
	gameChat = threading.Thread(target=start_chat, args=(players,))
	gameChat.start()
	turn = 0
	for i in players:
		i.initGame(players)
	while(True):
		for i in players:
			i.announce(str(players[turn].id) + "'s turn!")
		players[turn].takeTurn()
		turn = ((turn + 1) % len(players))

def start_chat(players):
	pass
	#todo


def main():
	mainThread = threading.Thread(target=start_server)
	mainThread.start()
	
	while(True):
		with client.Client.clientLock:
			while (len(client.Client.unattachedClientList) < NUM_PLAYERS):
				print("Waiting for other player.....")
				client.Client.clientLock.wait()

			connectedClients = client.Client.unattachedClientList
			#unattached clients are now attached
			client.Client.unattachedClientList = [];
		#We got here because we have enough players for a game, start a game on new thread
		gameThread = threading.Thread(target=start_game, args=(connectedClients,))
		gameThread.start()


if __name__ == "__main__":
  main()