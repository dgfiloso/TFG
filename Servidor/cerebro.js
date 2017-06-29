/**
*
*	@file 		websocket_server.js
*	@author 	David Gonzalez Filoso <dgfiloso@b105.upm.es>
*	@summary 	Servidor que escucha los sockets y los conecta entre ellos para enviarse archivos
*	@version	v2.4
*
**/

//	Importamos librerias
var express = require('express');
var body_parser = require('body-parser');
var app = express();
var web_server = require('http').Server(app);
var io = require('socket.io')(web_server);
var path = require("path");
var ws 	= require("nodejs-websocket");

//	Creamos el servidor
var server = ws.createServer();

//	Ponemos al servidor a escuchar en el puerto 3000
server.listen(3000, function()
{
	console.log("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n");
  console.log('Servidor corriendo en ws://localhost:3000');
});
//	Ponemos el servidor web a escuchar en el puerto 5000
web_server.listen(5000, function()
{
	console.log('Servidor web corriendo en http://localhost:5000');
});

/**
*	INTERACCIÓN WEBSOCKETS
**/
//	Arrays que contendrán los sockets y las habitaciones
var clients = [];
var rooms = 0;

//	Secuencia que envía cada segundo los bits que se están enviando
var bits_ts = 0;		//	Número de bits de transmisores a servidor
var bitRate_ts = 0;
var bits_sr = 0;		//	Número de bits de servidor a receptores
var bitRate_sr = 0;
function calc_bitRate()
{
	bitRate_ts = bits_ts;
	bitRate_sr = bits_sr;
	bits_ts = 0;
	bits_sr = 0;
	io.sockets.emit('refreshBitRate');
}
setInterval(calc_bitRate,1000);


//	Atendemos las conexiones
server.on('connection', function(conn)
{
	console.log("Nuevo mutante conectado");

	conn.sendText(JSON.stringify({event: "ACK", data: "Se ha conectado correctamente a Cerebro"}));

	conn.on('close', function(code, reason)
	{
		console.log("Desconectado mutante");
		for(var i in clients)
		{
			if(clients[i].socket === conn)
			{
				if(clients[i].type === "T")
				{
					rooms--;
					for (var j in clients)
					{
						if (clients[j].room === clients[i].room)
						{
							clients[j].room = 0;
						}
						else if (clients[j].room != 0)
						{
							clients[j].room--;
						}
					}
				}
				clients.splice(i,1);
				io.sockets.emit('refreshTable');
			}
		}
	});

	conn.on('error', function(err)
	{
		console.log("Connection Error: "+err);
	});

	conn.on('text', function(str)
	{
		var event = JSON.parse(str).event;

		/**
		*	Evento "info"
		*	@summary	Informa al servidor de sus características para que se incluya en el array
		**/
		if(event === "clientInfo")
		{
			var mutant_type = JSON.parse(str).type;
			var mutant_name = JSON.parse(str).name;
			//	Guardamos todos los datos del cliente en clients
			var clientInfo = new Object();
			clientInfo.socket = conn;
			clientInfo.type = mutant_type;
			clientInfo.name = mutant_name;
			clientInfo.room = 0;

			console.log("Añadido Mutante: { name: "+clientInfo.name+" type: "+clientInfo.type+" }");

			if(clientInfo.type === "T")
			{
				rooms++;
				clientInfo.room = rooms;
			}

			clients.push(clientInfo);
			//	Emitimos un mensaje para que los gestores web actualicen la tabla de su navegador
			io.sockets.emit('refreshTable');
		}

		/**
		*	Evento "pauseTx"
		*	@summary	Envia a todos los receptores el evento pauseTx
		**/
		else if (event === "pauseTx")
		{
			var data = JSON.parse(str).data;

			var txRoom = 0;
			for (var i in clients)
			{
				if(clients[i].socket === conn)
				{
					txRoom = clients[i].room;
				}
			}
			for (var i in clients)
			{
				if((clients[i].socket !== conn)&&(clients[i].type === "R")&&(clients[i].room === txRoom))
				{
					clients[i].socket.sendText(JSON.stringify({event: event, data: data}));
				}
			}
		}

		/**
		*	Evento "resumeTx"
		*	@summary	Envia a todos los receptores el evento resumeTx
		**/
		else if (event === "resumeTx")
		{
			var data = JSON.parse(str).data;

			var txRoom = 0;
			for (var i in clients)
			{
				if(clients[i].socket === conn)
				{
					txRoom = clients[i].room;
				}
			}
			for (var i in clients)
			{
				if((clients[i].socket !== conn)&&(clients[i].type === "R")&&(clients[i].room === txRoom))
				{
					clients[i].socket.sendText(JSON.stringify({event: event, data: data}));
				}
			}
		}

		/**
		*	Evento "endTx"
		*	@summary	Envia a todos los receptores el evento endTx
		**/
		else if (event === "endTx")
		{
			var data = JSON.parse(str).data;

			var txRoom = 0;
			for (var i in clients)
			{
				if(clients[i].socket === conn)
				{
					txRoom = clients[i].room;
				}
			}
			for (var i in clients)
			{
				if((clients[i].socket !== conn)&&(clients[i].type === "R")&&(clients[i].room === txRoom))
				{
					clients[i].room = 0;
					clients[i].socket.sendText(JSON.stringify({event: event, data: data}));
				}
			}
		}
	});

	conn.on('binary', function(inStream)
	{
		inStream.on('readable', function()
		{
			var txRoom = 0;
			var data = inStream.read();
			bits_ts += data.byteLength * 8;
			for (var i in clients)
			{
				if(clients[i].socket === conn)
				{
					txRoom = clients[i].room;
				}
			}
			for (var i in clients)
			{
				if((clients[i].socket !== conn)&&(clients[i].type === "R")&&(clients[i].room === txRoom))
				{
					// console.log("Client "+i+" : "+data.length);
					bits_sr += data.byteLength * 8;
					clients[i].socket.sendBinary(data);
				}
			}
		});
	});
});

/**
*	INTERACCIÓN HTTP
**/

io.on('connection', function(socket)
{
	// console.log("Gestor web conectado");
});

// view engine setup
app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'ejs');

//	Servir contenido estatico
app.use(express.static(path.join(__dirname,'public')));
app.use(body_parser.urlencoded({extended:true}));

/* GET home page. */
app.get('/', function(req, res, next)
{
	// console.log(clients);
	var tx = [];
	var rx = [];
	for (var i in clients)
	{
		if (clients[i].type === "T")
		{
			tx.push(clients[i]);
		}
		else if (clients[i].type === "R")
		{
			rx.push(clients[i]);
		}
	}
	res.render('index', {clients: clients, tx: tx, rx: rx, bitRate_ts: bitRate_ts, bitRate_sr: bitRate_sr});
});

/*	Rutas	*/
app.get('/room', function(req, res, next)
{
	var tx = [];
	var rx = [];
	for (var i in clients)
	{
		if (clients[i].type === "T")
		{
			tx.push(clients[i]);
		}
		else if (clients[i].type === "R")
		{
			rx.push(clients[i]);
		}
	}
	res.render('rx_room', {tx: tx, rx: rx});
});

app.get('/delete', function(req, res, next)
{
	res.render('delete', {clients: clients});
});

app.post('/room', function(req, res, next)
{
	for (var i in clients)
	{
		if (clients[i].name === req.body.rxName)
		{
			if (req.body.txName === "Desconectar")
			{
				clients[i].room = 0;
				clients[i].socket.sendText(JSON.stringify({event: "endTx", data: "ENDED COMMUNICATION"}));
			}
			else
			{
				for (var j in clients)
				{
					if (clients[j].name === req.body.txName)
					{
						clients[i].room = clients[j].room;
					}
				}
			}
		}
	}
	var tx = [];
	var rx = [];
	for (var i in clients)
	{
		if (clients[i].type === "T")
		{
			tx.push(clients[i]);
		}
		else if (clients[i].type === "R")
		{
			rx.push(clients[i]);
		}
	}
	res.redirect('/');
});

app.post('/delete', function(req, res, next)
{
	for (var i in clients)
	{
		if (clients[i].name === req.body.deleteName)
		{
			clients[i].socket.sendText(JSON.stringify({event: "endTx", data: "ENDED COMMUNICATION"}));
			clients.splice(i,1);
		}
	}
	var tx = [];
	var rx = [];
	for (var i in clients)
	{
		if (clients[i].type === "T")
		{
			tx.push(clients[i]);
		}
		else if (clients[i].type === "R")
		{
			rx.push(clients[i]);
		}
	}
	res.redirect('/');
});
