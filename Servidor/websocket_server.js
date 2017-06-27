/**
*
*	@file 		websocket_server.js
*	@author 	David Gonzalez Filoso <dgfiloso@b105.upm.es>
*	@summary 	Servidor que escucha los sockets y los conecta entre ellos para enviarse archivos
*	@version	v2.0
*
**/

//	Importamos librerias
var ws 	= require("nodejs-websocket");			//	Libreria para usar websockets

//	Creamos el servidor
var server = ws.createServer();

//	Ponemos al servidor a escuchar en el puerto 3000
server.listen(3000, function(){
	console.log("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n");
    console.log('Servidor corriendo en ws://localhost:3000');
});

//	Arrays que contendran los sockets
var clients = [];

//	Atendemos las conexiones
server.on('connection', function(conn) {

	console.log("Nuevo mutante conectado");

	conn.sendText(JSON.stringify({event: "ACK", data: "Se ha conectado correctamente a Cerebro"}));

	conn.on('close', function(code, reason) {
		console.log("Desconectado mutante");
		for(var i in clients) {
			if(clients[i].socket === conn) {
				clients.splice(i,i);
			}
		}
	});

	conn.on('error', function(err) {
		console.log("Connection Error: "+err);
	});

	conn.on('text', function(str) {

		var event = JSON.parse(str).event;
		var data = JSON.parse(str).data;

		/**
		*	Evento "info"
		*	@summary	Informa al servidor de sus características para que se incluya en el array
		**/
		if(event === "clientInfo"){

			//	Guardamos todos los datos del cliente en clients
			var clientInfo = new Object();
			clientInfo.socket = conn;
			clientInfo.type = data;

			console.log("Añadido Mutante: { type: "+clientInfo.type+" }");

			if(clientInfo.type === "T") {

				//	Si el cliente es un transmisor, le enviamos un mensaje para que comience a transmitir
				conn.sendText(JSON.stringify({event: "envio"}));
				console.log("Enviada peticion para transmitir archivo");

			}

			clients.push(clientInfo);

		}

		/**
		*	Evento "pausedTx"
		*	@summary	Envia a todos los receptores el evento pausedTx
		**/
		else if (event === "pausedTx")  {

			var data = JSON.parse(str).data;

			for (var i in clients) {
				if((clients[i].socket !== conn)&&(clients[i].type === "R")) {
					clients[i].socket.sendText(JSON.stringify({event: event, data: data}));
				}
			}
		}

		/**
		*	Evento "resumeTx"
		*	@summary	Envia a todos los receptores el evento resumeTx
		**/
		else if (event === "resumeTx")  {

			for (var i in clients) {
				if((clients[i].socket !== conn)&&(clients[i].type === "R")) {
					clients[i].socket.sendText(JSON.stringify({event: event, data: data}));
				}
			}
		}

		/**
		*	Evento "endTx"
		*	@summary	Envia a todos los receptores el evento endTx
		**/
		else if (event === "endTx")  {

			for (var i in clients) {
				if((clients[i].socket !== conn)&&(clients[i].type === "R")) {
					clients[i].socket.sendText(JSON.stringify({event: event, data: data}));
				}
			}
		}
	});

	conn.on('binary', function(inStream) {

		inStream.on('readable', function() {

			for (var i in clients){
				if((clients[i].socket !== conn)&&(clients[i].type === "R")){

					clients[i].socket.sendBinary(inStream.read());
				}
			}
		});
	});
});
