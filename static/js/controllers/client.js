(function() {
	clientModule.factory('client', function(socket) {
		var constructor = function() {
			this.id = null;
			this.name = null;
			this.turn = false;
			this.hand = [];
			this.kingdom = {};
			this.baseSupply = {};
			this.actions = 0;
			this.buys = 0;
			this.balance = 0;
			this.played = [];
			this.spendableMoney = 0;
			//mode overidden by turn
			this.modeJson = {"mode":"action"}; //.mode = action, buy, select, gain, wait, gameover
			var that = this;

			//socket
			this.onmessage = function(event){
				var jsonres = JSON.parse(event.data);
				var exec = that[jsonres.command];
				if (exec != undefined){
					exec.call(that,jsonres);
				}
			};
		};

		constructor.prototype.init = function(json) {
				this.id = json.id;
				this.name = json.name;
		};

		constructor.prototype.updateHand = function(json){
			this.hand = json.hand;
			this.updateSpendable();
		};

		constructor.prototype.announce = function(json){
				$('#msg').append("<br>" + json.msg);
				$("#container").scrollTop($(document).height());
				$("#msg").scrollTop($("#msg")[0].scrollHeight);
		};

		constructor.prototype.kingdomCards = function(json){
			var kingdomArray = JSON.parse(json.data);
			for (var i=0; i< kingdomArray.length; i++) {
				this.kingdom[kingdomArray[i].title] = kingdomArray[i];			
			}
		};

		constructor.prototype.baseCards = function(json){
			var baseArray = JSON.parse(json.data);
			for (var i=0; i< baseArray.length; i++) {
				this.baseSupply[baseArray[i].title] = baseArray[i];			
			}
		};

		constructor.prototype.startTurn = function(json){
			this.turn = true;
			this.updateResources(json);
			this.spendableMoney = 0;
			this.updateSpendable();
		};

		constructor.prototype.updateMode = function(json){
			this.modeJson = json;
		};

		constructor.prototype.endTurn = function(){
			this.turn = false;
			this.discard(this.hand);
			this.played = []; //discarded on backend
			socket.send(JSON.stringify({"command": "endTurn"}));
		};

		constructor.prototype.discard = function(cards){
			if (cards.length == 0){
				return;
			}
			var cardsByTitle = $.map(cards, function(val, index){
				return val.title;
			});
			socket.send(JSON.stringify({"command": "discard", "cards": cardsByTitle}));
			//remove from hand
			for (var j=0; j<cards.length; j++){
				for (var i=0; i<this.hand.length; i++){
					if (cards[j] == this.hand[i]){
						this.hand.splice(i,1);
						i--;
					}
				}
			}
		};

		constructor.prototype.updateSpendable = function (){
			this.spendableMoney = 0;
			for (var i=0; i<this.hand.length; i++){
				if (this.hand[i].type === "Money"){
					this.spendableMoney += this.hand[i].value;
				}
			}
		};

		constructor.prototype.spendAllMoney = function(){
			this.spendableMoney = 0;
			this.modeJson = {"mode":"buy"};
			socket.send(JSON.stringify({"command": "spendAllMoney"}));
		};

		constructor.prototype.playCard = function(card){

			if (this.actions > 0 || card.type.indexOf("Action") === -1){
				socket.send(JSON.stringify({"command":"play", "card": card.title}));
				this.played.push(card);
				//remove from hand
				for (var i=0; i<this.hand.length; i++){
					if (card == this.hand[i]){
						this.hand.splice(i,1);
						i--;
					}
				}
			}

			if (card.type === "Money"){
				this.modeJson = {"mode":"buy"};
				this.updateSpendable();
			}

		};

		constructor.prototype.buyCard = function(card){
			if (this.balance >= card.price){
				this.buys -= 1;
				this.balance -= card.price;
				socket.send(JSON.stringify({"command":"buyCard", "card": card.title}));
			}
		};

		constructor.prototype.updatePiles = function(json){
			if (json.card in this.kingdom){
				this.kingdom[json.card].count = json.count;
			} else {
				this.baseSupply[json.card].count = json.count;
			}
		};

		constructor.prototype.updateResources = function(json){
			this.actions = json.actions;
			this.buys = json.buys;
			this.balance = json.balance;
			if (this.modeJson.mode === "buy" && this.buys === 0){
				this.endTurn();
			}
		};

		constructor.prototype.getHand = function(){
			return this.hand;
		};

		constructor.prototype.getTurn = function(){
			return this.turn;
		};

		constructor.prototype.getActions = function(){
			return this.actions;
		};

		constructor.prototype.getBalance = function(){
			return this.balance;
		};

		constructor.prototype.getBuys = function(){
			return this.buys;
		};

		constructor.prototype.getKingdom = function(){
			return this.kingdom;
		};
		
		constructor.prototype.getBaseSupply = function(){
			return this.baseSupply;
		};

		constructor.prototype.getSpendableMoney = function(){
			return this.spendableMoney;
		};

		constructor.prototype.getModeJson = function(){
			return this.modeJson;
		};

		constructor.prototype.getName = function(){
			return this.name;
		};

		return new constructor();
	});

	clientModule.controller("clientController", function($rootScope, $scope, socket, client){
		$scope.c = client;
		$scope.hand = client.getHand();
		$scope.turn = client.getTurn();
		$scope.actions = client.getActions();
		$scope.buys = client.getBuys();
		$scope.balance = client.getBalance();
		$scope.kingdom = client.getKingdom();
		$scope.baseSupply = client.getBaseSupply();
		$scope.spendableMoney = client.getSpendableMoney();
		$scope.modeJson = client.getModeJson();

		$scope.$on("$destroy", function(){
			socketlistener();
		});
		socket.send(JSON.stringify({"command": "ready", "name": client.name}));
		var socketlistener = $rootScope.$on("socketmsg", function(data, event){
			client.onmessage(event);
			$scope.$apply(function(){
				$scope.hand = client.getHand();
				$scope.turn = client.getTurn();
				$scope.actions = client.getActions();
				$scope.buys = client.getBuys();
				$scope.balance = client.getBalance();
				$scope.kingdom = client.getKingdom();
				$scope.baseSupply = client.getBaseSupply();
				$scope.spendableMoney = client.getSpendableMoney();
				$scope.modeJson = client.getModeJson();
			});
		});

		$scope.returnLobby = function(){
			$scope.main.game = false;
			socket.send(JSON.stringify({"command": "returnToLobby"}));
		};

	});
	
	clientModule.controller("handController", function($scope, client, cardStyle){
		$scope.disabled = function(card){
			if (card.type === "Victory" || card.type === "Curse" || $scope.turn === false || $scope.modeJson.mode === "wait"
				|| $scope.modeJson.mode === "select" || $scope.modeJson.mode === "gain"){
				return true;
			}
			if ($scope.modeJson.mode === "buy"){
				if (card.type.indexOf("Action") !== -1){
					return true;
				}
			}
			return false;
		};

		$scope.clickCard = function(card){
			client.playCard(card);
		};

		$scope.getButtonStyle = cardStyle.getButtonStyle;
	});

	clientModule.controller("supplyController", function($scope, socket, client, cardStyle){
		var getSupplyArray = function(supply){
			return $.map(supply, function(card, title){
				return card;
			});
		};

		$scope.kingdomSupplyArray = getSupplyArray($scope.kingdom);
		$scope.baseSupplyArray = getSupplyArray($scope.baseSupply);

	    $scope.$watch('kingdom', function(newValue, oldValue) {
			$scope.kingdomSupplyArray = getSupplyArray($scope.kingdom);
    	}, true);
	    $scope.$watch('baseSupply', function(newValue, oldValue) {
			$scope.baseSupplyArray = getSupplyArray($scope.baseSupply);
    	}, true);

		$scope.disabled = function(card){
			if (card.title in $scope.kingdom && $scope.kingdom[card.title].count === 0 || 
				card.title in $scope.baseSupply && $scope.baseSupply[card.title].count === 0){
				return true;
			}

			if ($scope.turn && $scope.modeJson.mode === "buy"){
				return card.price > $scope.balance;
			}
			if ($scope.modeJson.mode === "gain"){
				if ($scope.modeJson.equal_only){
					return card.price !== $scope.modeJson.price;
				} else {
					return card.price > $scope.modeJson.price;
				}
			}
			return (!$scope.turn || $scope.modeJson.mode === "wait" || $scope.modeJson.mode === "action");
		};

		$scope.clickCard = function(card){
			if ($scope.modeJson.mode === "gain"){
				//refactor into method (?)
				socket.send(JSON.stringify({"command": "gain", "card": card.title}));
			} else {
				client.buyCard(card);
			}
		};

		$scope.getButtonStyle = cardStyle.getButtonStyle;
	});

	clientModule.controller("selectController", function($scope, socket){
	    $scope.$watch('modeJson', function(newValue, oldValue) {
			if ($scope.modeJson.count){
				$scope.canBeDone = false;
			} else {
				$scope.canBeDone = true;
			}
    	});

		$scope.selected = [];
		$scope.check = function(option, isChecked){
			if ($scope.modeJson.count != undefined){
				var checkedCount = $("input:checkbox:checked").length;
				if (checkedCount >= $scope.modeJson.count){
					$("input:checkbox").not(":checked").attr("disabled", true);
					$scope.canBeDone = true;
				} else {
					$("input:checkbox").not(":checked").attr("disabled", false);
					$scope.canBeDone = false;
				}
			}

			if (isChecked){
				$scope.selected.push(option);
			} else {
				var i = $scope.selected.indexOf(option);
				$scope.selected.splice(i,1);
			}
		};

		$scope.selectOne = function(option){
			$scope.selected.push(option);
			$scope.doneSelection();
		};

		$scope.doneSelection = function(){
			socket.send(JSON.stringify({"command": "post_selection", "selection": $scope.selected, "act_on":$scope.modeJson.act_on}));
			$scope.selected = [];
		};

	});

})();

