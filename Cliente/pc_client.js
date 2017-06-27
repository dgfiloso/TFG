/**
*
*	@file		pc_client.js
*	@author 	David Gonzalez Filoso <dgfiloso@b105.upm.es>
*	@summary 	Cliente para ordenador. Puede ser tanto receptor como transmisor
*	@version 	v1.0
*
**/

/**	IMPORTAMOS LIBRERIAS	**/

var io = require("socket.io-client");		//	Libreria para clientes de socket.io
var ss = require("socket.io-stream");		//	Libreria para usar streams con socket.io
var fs = require("fs");						//	Libreria para acceder al sistema de archivos
var path = require("path");					//	Libreria para resolver rutas
var child = require("child_process");		//	Libreria para crear subprocesos
var ffmpeg = require("fluent-ffmpeg");		//	Libreria para usar ffmpeg
var Speaker = require("speaker");			//	Libreria para reproducir audio PCM en los altavoces
var lame = require("lame");					//	Libreria para codicficar/decodificar audio


/**		CÓDIGO DEL CLIENTE 		**/

//	Tipo de cliente
var tipoMutante;

//	Variable donde guardaremos el proceso ffmpeg
var command;

//	Variable con el numero del bus de la tarjeta de sonido del sistema
var soundCard;

//	Conexion con el servidor, sustituir localhost por la IP del servidor
var socket = io.connect('http://localhost:3000', {'forceNew' : true});


/**
*	Evento "ACK"
*	@summary	Se encarga de recibir la confirmacion de que se ha conectado el
*				cliente al servidor y que además le envía su tipo
**/
socket.on('ACK', function(data){

	console.log("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n");
	console.log(data);
	var info;

	console.log("¿Que tipo de Mutante eres (T o R)?");

	//	Iniciamos la lectura del teclado
	process.stdin.resume();
	process.stdin.setEncoding('utf8');

	//	Tomamos los datos del teclado y enviamos los datos al servidor
	process.stdin.on('data', function(text1) {
		if(text1 === 'R\n' || text1 === 'T\n'){
			tipoMutante = text1.split("\n")[0];

			info = {type : tipoMutante};
			socket.emit('clientInfo', info);

			//	Pausamos la lectura del teclado
			process.stdin.pause();

			if (tipoMutante === 'R'){
				console.log("Preparado para reproducir...");
			}
		}
	});
});

/**
*	Evento del proceso 'SIGINT'
*	@summary	Detectamos la interrupcion del cliente para cerrar la conexion
**/
process.on('SIGINT', function() {

    console.log("\nCerrando la conexion del Mutante\n\n\n\n\n\n\n\n\n\n\n\n");
    socket.emit('close');
    process.exit();
});


/**
*	Evento "envio"
*	@summary	Se encarga de enviar un stream de un fichero al servidor
**/
socket.on('envio', function() {

	//	Pedimos si desea enviar un fichero (F) o lo que se está reproduciendo (A)
	console.log("¿Desea enviar un archivo (F) o enviar lo que está escuchando (A) ?");

	process.stdin.resume();
	process.stdin.on('data', function(text) {
		var res = text.split("\n")[0];

		if (res === "F") {

			//	Pedimos si desea enviar al servidor(S) o a los receptores (R)
			console.log("¿Desea enviarlo al servidor (S) o a todos los receptores (AR) ?");

			process.stdin.on('data', function(text) {
				var res = text.split("\n")[0];
				if(res === "S") {
					//	Detenemos la lectura
					process.stdin.pause();
					var rx = "S";

					sendFile(ss, rx);

				} else if (res === "AR") {
					//	Detenemos la lectura
					process.stdin.pause();
					var rx = "AR";

					sendFile(ss, rx);

				} else {
					console.log("SR - Respuesta no valida");
				}
			});

		} else if (res === "A") {

			//	Pedimos si desea enviar al servidor(S) o a los receptores (R)
			console.log("¿Desea enviarlo al servidor (S) o a todos los receptores (AR) ?");

			process.stdin.on('data', function(text) {
				var res = text.split("\n")[0];
				if(res === "S") {
					//	Detenemos la lectura
					process.stdin.pause();
					var rx = "S";

					sendAudio(ss, child, rx);

				} else if (res === "AR") {
					//	Detenemos la lectura
					process.stdin.pause();
					var rx = "AR";

					console.log("Vamos a ejecutar la funcion");
					sendAudio(ss, child, rx);

				} else {
					console.log("SR - Respuesta no valida");
				}
			});

		} else {
			console.log("AF - Respuesta no valida");
		}
	});

});

/**
*	Evento "broadcastRx"
*	@summary	Se encarga de recibir un stream y reproducirlo
**/
ss(socket).on('broadcastRx', function(stream, data) {

	//	Creamos un objeto de tipo Decoder
	var decoder = new lame.Decoder();

	//	Pasamos nuestro stream por el decodificador
	stream.pipe(decoder).on('format', function(format) {

		//	Creamos un objeto de tipo Speaker
		speaker = new Speaker(format);

		//	Enviamos nuestro stream a través del objero Speaker para que se reproduzca
		this.pipe(speaker);
	})
    console.log("Reproduciendo...");
});

/**		DEFINICION DE FUNCIONES		**/

/**
*	@function 			sendFile(ss, rx)
*	@description		Se encarga de enviar un fichero mediante un stream
*	@param				ss: 	Objeto de tipo socket-io.stream
*	@param	{string}	rx: 	Variable que indica quien es el receptor (S o R)
**/
function sendFile(ss, rx){

	console.log("Indique la ruta del fichero que desea enviar");

	//	Creamos un stream
	var stream = ss.createStream();

	//	Pedimos el archivo a enviar
	process.stdin.resume();
	process.stdin.setEncoding('utf8');
	process.stdin.on('data', function(text) {
		var ruta = text.split("\n")[0];
		console.log("Enviamos el archivo con ruta: "+ruta);

		//	Creamos un stream de lectura y lo encaminamos al stream que vamos a enviar
		fs.createReadStream(ruta).pipe(stream);

		if (rx === "S")  {

			//	Emitimos al servidor el stream junto a la ruta
			ss(socket).emit('send2Server', stream, {filename: ruta, type: "F"});

		} else if (rx === "AR") {

			//	Emitimos al servidor el stream, el nombre del fichero será el último elemento tras "/"
			ss(socket).emit('broadcastTx', stream, {filename: ruta, type: "F"});

		}

		process.stdin.pause();
	});

}


/**
*	@function			sendAudio(ss, child)
*	@param				ss: 	Objeto de tipo socket-io.stream
*	@param				child: 	Objeto de tipo child_process
*	@param	{string}	rx: 	Variable que indica quien es el receptor (S o R)
**/
function sendAudio(ss, child, rx) {

	//	Obetenemos el numero del bus de la tarjeta de sonido
	child.exec('pacmd list-cards | grep device.bus_path', function(error, stdout, stderr) {

		soundCard = stdout.split('"')[1];
		console.log("Numero del bus de la tarjeta de sonido: "+soundCard);

		//	Cambiamos los dos puntos del numero a barra baja (Usamos expresiones regulares para que cambien todos)
		soundCard = soundCard.replace(/:/g, "_");

		console.log("Vamos a ejecutar: "+'pacmd set-default-source alsa_output.'+soundCard+'.analog-stereo.monitor');
		//	Cambiamos el micrófono a Monitor of
		child.exec('pacmd set-default-source alsa_output.'+soundCard+'.analog-stereo.monitor');

		if (command !== undefined) {

			command.kill('SIGCONT');

			//	Cerramos la captura de audio
			process.stdin.resume();
			process.stdin.setEncoding('utf8');
			process.stdin.on('data', function(text) {
				if(text.split("\n")[0] === ":q") {

					process.stdin.pause();

					console.log("Cortando captura");
					//	Escribimos en el stdin del script el comando de detención
					command.kill('SIGSTOP');

					//	Volvemos a poner el micrófono en su estado predeterminado
					child.exec('pacmd  set-default-source alsa_input.pci-0000_00_1b.0.analog-stereo');

					socket.emit('endTx');

				}
			});

		} else {

			//	Comando en terminal: ffmpeg -f alsa -i pulse <salida>
			command = ffmpeg('pulse')
			.inputOptions(['-f alsa'])
			.on('start', function(cmdline)  {
				console.log('Command line: ' + cmdline);
				console.log('Comenzamos la captura...\n')
			})
			.on('progress', function(progress) {
				console.log('Processing: '+progress.percent+'% done');
			})
			// .on('stderr', function(stderrLine) {
			// 	console.log('Stderr output: '+stderrLine);
			// })
			.on('end', function() {
				console.log('Captura y conversion finalizada con exito');
			})
			.outputFormat('mp3')

			if(rx === "S") {

				//	Creamos el stream que vamos a enviar
				var stream = ss.createStream();

				//	Sacamos los datos de ffmpeg y los encaminamos al stream
				command.pipe(stream);

				console.log("Enviamos el stream de audio al servidor");

				//	Emitimos al servidor el stream
				ss(socket).emit('send2Server', stream, {filename: "audioTx.mp3", type: "A"});
				console.log("Audio enviado al servidor");

			} else if (rx === "AR") {

				//	Creamos el stream que vamos a enviar
				var stream = ss.createStream();

				//	Sacamos los datos de ffmpeg y los encaminamos al stream
				command.pipe(stream);

				console.log("Enviamos el stream de audio a los receptores");

				//	Emitimos al servidor el stream
				ss(socket).emit('broadcastTx', stream, {filename: "audioTx.mp3", type: "A"});
				console.log("Audio enviado a los clientes");
			}

			//	Cerramos la captura de audio
			process.stdin.resume();
			process.stdin.setEncoding('utf8');
			process.stdin.on('data', function(text) {
				if(text.split("\n")[0] === ":q") {

					process.stdin.pause();

					console.log("Cortando captura");
					//	Escribimos en el stdin del script el comando de detención
					command.kill('SIGSTOP');

					//	Volvemos a poner el micrófono en su estado predeterminado
					child.exec('pacmd  set-default-source alsa_input.pci-0000_00_1b.0.analog-stereo');

					socket.emit('endTx');

				}
			});
		}
	});
}
