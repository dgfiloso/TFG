/**
*
*	@file 		main.js
*	@author 	David Gonzalez Filoso <dgfiloso@b105.upm.es>
*	@summary 	Servidor que escucha los sockets y los conecta entre ellos para enviarse archivos
*	@version	v1.0
*
**/

/**	Creamos los objetos para poder usar las librerias	**/
var express = require('express');  						//	Libreria para poder usar express
var app = express();  												//	Objeto de express para poder crear el servidor
var server = require('http').Server(app);			//	Libreria para crear el servidor
var io = require('socket.io')(server);				//	Libreria que inicia un servidor socket.io
var ss = require("socket.io-stream");					//	Libreria para usar streams con socket.io
var fs = require("fs");												//	Libreria para acceder al sistema de archivos
var path = require("path");										//	Libreria para resolver rutas
var ffmpeg = require("fluent-ffmpeg");				//	Libreria para usar ffmpeg

//	Ponemos el servidor a escuchar en el puerto 3000
server.listen(3000, function() {

	console.log("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n");
    console.log('Servidor corriendo en http://localhost:3000');
});


/**		INTERACCION CON LOS SOCKETS 	**/

//	Arrays que contendran los sockets
var clients = [];
var tx = [];
var rx = [];

/**
*	Evento "connection"
*	@summary	Conexion de un socket
**/
io.on('connection', function(socket){

	//	Mostramos y enviamos una confirmacion de la conexion
	console.log("Mutante conectado");
	socket.emit('ACK', "Se ha conectado correctamente a Cerebro");

	/**
	*	Evento "clientInfo"
	*	@summary	Recibimos los datos del cliente y los guardamos en nuestro array
	**/
	socket.on('clientInfo', function(data){

		//	Guardamos todos los datos del cliente en clients
		var clientInfo = new Object();
		clientInfo.socket = socket;
		clientInfo.id = socket.id;
		clientInfo.type = data.type;
		clientInfo.name = data.name;

		console.log("Añadido Mutante: { name: "+clientInfo.name+" , type: "+clientInfo.type+" , id: "+clientInfo.id+" }");

		if(clientInfo.type === "T") {

			clientInfo.tx = 0;
			clientInfo.stream = undefined;

			tx.push(clientInfo);

			//	Si el cliente es un transmisor, le enviamos un mensaje para saber si quiere transmitir
			socket.emit('envio');
			console.log("Enviada peticion para transmitir archivo");

		} else {

			rx.push(clientInfo);

			//	Miramos si algun cliente se encuentra trasmitiendo para recibir el stream
			for (var i in clients) {
				if(clients[i].tx === 1) {

					console.log("Se ha conectado un receptor mientras retransmitimos");

					//	Le enviamos el stream al receptor
					var newStream = ss.createStream();
					clients[i].stream.pipe(newStream);
					ss(clientInfo.socket).emit('broadcastRx', newStream);
					console.log("Enviada al receptor "+clientInfo.id);
				}
			}
		}

		clients.push(clientInfo);
	});

	/**
	*	Evento "close"
	*	@summary	Al cerrar un socket lo eliminamos de la lista
	**/
	socket.on('close', function(data) {

		//	Buscamos el cliente y lo eliminamos del array
		for (var i in clients) {
			if(clients[i].id === socket.id) {
				clients.splice(i,i);
			}
		}
		console.log("Desconectado mutante con id: "+socket.id);

		//	Emitimos un mensaje para que los clientes actualicen la tabla de su navegador
		io.sockets.emit('refreshTable');
	});

	/**
	*	Evento "send2Server"
	*	@summary	Recepción de un archivo por parte de un transmisor y guardado en el servidor
	**/
	ss(socket).on('send2Server', function(stream, data) {

		//	Obtenemos el nombre del fichero a partir de la ruta
		var filename = path.basename(data.filename);

		//	Creamos un fichero local con el contenido del stream
		stream.pipe(fs.createWriteStream(filename));
		console.log("Archivo recibido");


		//	Volvemos a enviar un mensaje para saber si quiere transmitir
		socket.emit('envio');
		console.log("Enviada peticion para transmitir archivo");
	});

	/**
	*	Evento "broadcastTx"
	*	@summary	Transmisor envía archivo broadcast a todos los receptores (tipo = R)
	**/
	ss(socket).on('broadcastTx',	function(stream, data) {

		//	Indicamos que nuestro cliente esta trasmitiendo
		for (var i in clients) {
			if(clients[i].id === socket.id) {
				clients[i].tx = 1;
				clients[i].stream = stream;
			}
		}

    	console.log("Enviando archivo de "+socket.id+" a todos los receptores");

    	//	Creamos un stream para cada receptor y encaminamos el stream recibido
    	for (var i in clients) {
    		if(clients[i].type !== "T") {
    			console.log("Socket: "+clients[i].id+" Tipo: "+clients[i].type);
    			var newStream = ss.createStream();
				stream.pipe(newStream);
				ss(clients[i].socket).emit('broadcastRx', newStream);
				console.log("Enviada al receptor "+clients[i].id);
    		}
    	}
	});

	/**
	*	Evento "endTx"
	*	@summary	Indica el final de la transmisión
	**/
	socket.on('endTx', function() {

		//	Buscamos el socket en clients para cambiar tx y stream
		for (var i in clients) {
			if(clients[i].id === socket.id) {
				clients[i].tx = 0;
				clients[i].stream = undefined;
			}
		}

		//	Enviamos la peticion para volver a transmitir
		socket.emit('envio');
		console.log("Enviada peticion para transmitir archivo");

	})
});
