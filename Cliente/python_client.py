#! /usr/bin/env python
# -*- coding: utf-8 -*-

import threading	#	Librería para usar distintas hebras
import json			#	Librería para usar objetos JSON
import subprocess	#	Librería para usar procesos del sistema
import sys			#	Librería para usar el sistema
try:
	import websocket 	#	Librería para usar websockets
except ImportError:
	import pip
	pip.main(['install','--user','websocket-client'])
	try:
		import websocket
	except ImportError:
		import websocket
#	Librerías de GStreamer
try:
	import gi
except ImportError:
	print "#Error: Gstreamer not installed"
	print "\t Execute 'sudo apt-get install gstreamer1.0 gstreamer1.0-*'"
	print "\t Execute 'sudo apt-get install python-gst-1.0'"
	sys.exit();

gi.require_version('Gst','1.0')
gi.require_version('Gtk','3.0')
from gi.repository import GObject, Gtk
from gi.repository import Gio as gio
from gi.repository import Gst as gst

OPCODE			= 1			#	Variable que guarda el valor del opcode del último mensaje
mutant_type 	= None		#	Variable que guarda el tipo de mutante del cliente
mutant_name 	= None		#	Variable que guarda el nombre del mutante
buff_Rx			= gio.MemoryInputStream()	#	Memoria que guarda los datos de entrada
tx_pipeline     = None		#	Variable que guarda el pipeline de transmisión
rx_pipeline 	= None		#	Variable que guarda el pipeline de recepción
play			= 0			#	Variable que se usa para esperar 20 paquetes antes de empezar a reproducir

GObject.threads_init()
gst.init(None)
#	Descomentar para ver las trazas de GStreamer y detectar posibles errores
# gst.debug_set_active(True)
# gst.debug_set_default_threshold(3)


def control_Tx(conn):
	"""Controla la transmisión del flujo de datos.

	Inicia una lectura del teclado para controlar el pipeline de transmisión.

	Comandos:

	:p -- Pausa la transmisión
	:r -- Continua la transmisión
	:q -- Finaliza la transmisión

	Si la transmisión es finalizada no se puede volver a iniciar

	"""
	print "\n\n"
	print "	-------- Comandos de control:"
	print "	-------- :p -> Pausar"
	print "	-------- :r -> Continuar (Despues de pausar)"
	print "	-------- :q -> Finalizar"
	print "\n\n"
	comando = raw_input()
	while True:
		if comando  == ':p':
			conn.send(json.dumps({"event": "pausedTx", "data": "PAUSE"}))
			tx_pipeline.set_state(gst.State.PAUSED)
			print "PAUSE"
		elif comando == ':r':
			conn.send(json.dumps({"event": "resumeTx", "data": "RESUME"}))
			tx_pipeline.set_state(gst.State.PLAYING)
			print "RESUME"
		elif comando == ':q':
			conn.send(json.dumps({"event": "endTx", "data": "ENDED COMMUNICATION"}))
			tx_pipeline.set_state(gst.State.NULL)
			sys.exit();
			print "ENDED COMMUNICATION"
			break

		comando = raw_input()

def player():
	"""Reproduce los datos recibidos.

	Se utiliza la librería de GStreamer para crear un pipeline donde se toma
	un stream de recepción en MP3, se descodifica y se reproduce.

	Elementos del pipeline de recepción:

	-	giostreamsrc	-- Crea un stream a partir de un objeto tipo GMemoryInputStream
	-	man 			-- Decodifica el audio de MP3  a PCM para ser reproducido en los altavoces
	-	audioconvert	-- Elemento utilizado para la conversión
	-	pulsesink		-- Reproduce el audio en los altavoces

	"""

	print "Reproduciendo..."
	global rx_pipeline

	rx_pipeline = gst.Pipeline()

	audio_src 	= gst.ElementFactory.make("giostreamsrc","audio_src")
	decode 		= gst.ElementFactory.make("mad","decode")
	convert		= gst.ElementFactory.make("audioconvert", "convert")
	audio_sink 	= gst.ElementFactory.make("pulsesink","audio_sink")

	audio_src.set_property('stream',buff_Rx)

	rx_pipeline.add(audio_src)
	rx_pipeline.add(decode)
	rx_pipeline.add(convert)
	rx_pipeline.add(audio_sink)

	audio_src.link(decode)
	decode.link(convert)
	convert.link(audio_sink)

	rx_pipeline.set_state(gst.State.PLAYING)

	GObject.MainLoop().run()

def on_new_buffer(appsink):
	"""Enviamos los datos del pipeline de transmisión por los sockets.

	Esta función salta cuando el pipeline de transmisión emite una señal
	de tipo 'new-sample'. Se encarga de enviar esos datos a través de los sockets.

	"""

	tx_buffer = appsink.emit('pull-sample').get_buffer()
	tx_data = tx_buffer.extract_dup(0, tx_buffer.get_size())
	conn.send(tx_data, websocket.ABNF.OPCODE_BINARY)
	return False

def on_new_preroll(appsink):
	"""Indica que vamos a empezar a transmisitir.

	Esta función salta cuando el pipeline de transmisión emite una señal
	de tipo 'new-preroll'. Se encarga de avisar de que vamos a comenzar a
	transmitir.

	Los datos de preroll son datos de control, siempre salta uno antes de
	transmitir, por ello lo utilizamos para avisar al usuario.

	"""
	print "Transmitiendo..."
	return False


def send_audio(conn):
	"""Tomamos el audio del sistema y lo transmitimos mediante sockets.

	Esta función se puede dividir en dos partes claras:

	1.	Buscamos el número de nuestra tarjeta de sonido y cambiamos la entrada
		de audio a 'Monitor of' para crear un enlace entre los altavoces y
		el micrófono.

	2.	Creamos un pipeline de transmisión que lee el micrófono y envía sus
		datos mediante sockets.

	Elementos del pipeline de transmisión:

	-	pulsesrc		-- Lee los datos del micrófono
	-	audioconvert	-- Elemento usado para la conversión
	-	lamemp3enc		-- Convierte los datos del micrófono a MP3
	-	appsink			-- Elemento utilizado para obtener los datos y transmitirlos

	"""

	global tx_pipeline

	p = subprocess.Popen(['pacmd', 'list-cards'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	g = subprocess.Popen(['grep', 'device.bus_path'],stdin=p.stdout, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	soundCard = g.stdout.read().split('"')[1]
	print "Numero del bus de la tarjeta de sonido: "+soundCard
	soundCard = soundCard.replace(":","_")

	print "Vamos a ejecutar: "+'pacmd set-default-source alsa_output.'+soundCard+'.analog-stereo.monitor'
	subprocess.call(['pacmd', 'set-default-source', 'alsa_output.'+soundCard+'.analog-stereo.monitor'])

	#	Implementación con GStreamer
	tx_pipeline = gst.Pipeline()

	audio_src 	= gst.ElementFactory.make("pulsesrc","audio_src")
	convert		= gst.ElementFactory.make("audioconvert", "convert")
	encoder		= gst.ElementFactory.make("lamemp3enc","encoder")
	audio_sink	= gst.ElementFactory.make("appsink", "audio_sink")

	audio_sink.set_property('emit-signals', True)	#	Permite emitir las señales 'new-sample' y 'new-preroll'
	audio_sink.set_property('sync', False)			# 	Hace la decodificacion lo mas rapida posible
	audio_sink.connect('new-sample', on_new_buffer)
	audio_sink.connect('new-preroll', on_new_preroll)

	tx_pipeline.add(audio_src)
	tx_pipeline.add(convert)
	tx_pipeline.add(encoder)
	tx_pipeline.add(audio_sink)

	audio_src.link(convert)
	convert.link(encoder)
	encoder.link(audio_sink)

	tx_pipeline.set_state(gst.State.PLAYING)

	d = threading.Thread(target=control_Tx(conn))
	d.setDaemon(True)
	d.start()

	GObject.MainLoop().run()


def on_error(conn, err):
	"""Imprime errores de los sockets.

	"""
	print "Websocket connection Error: "+err

def on_close(conn):
	"""Informa del cierre de la conexión entre el socket y el servidor.

	"""
	print "Cerrada conexion con el servidor"

def on_open(conn):
	"""Informa de la creación correcta del cliente.

	"""
	print "\n\n\n\n"
	print "Cliente creado..."

def on_data(conn, str, dType, flag):
	"""Lee el opcode del mensaje que ha llegado y lo escribe en la variable OPCODE.

	"""

	global OPCODE

	OPCODE = dType

def on_message(conn, msg):
	"""Al llegar un mensaje, lo procesa en función primero de su opcode y
	después en función del evento.

	Esta función primero mira el opcode del mensaje.

	Si es 1 (un texto) mira el evento del mensaje y realiza una serie
	de tareas en función de él.

	Si es 2 (datos binarios) los añade a una memoria y lanza la función para
	reproducirlos.

	Eventos:

	-	ACK 		-- Indica que nos hemos conectado al servidor y le mandamos los datos del cliente.
	-	envio 		-- Solo lo reciben los clientes transmisores y se utiliza para comenzar la transmisión.
	-	pausedTx 	-- Pausa la reproducción del pipeline de recepción.
	-	resumeTx 	-- Continúa la reproducción del pipeline de recepción.
	-	endTx 		-- Finaliza la reproducción del pipeline de recepción.

	Cuando los datos recibidos son binarios, esperamos la llegada de varios paquetes,
	en nuestro caso 20, antes de comenzar a reproducir para llenar un poco la memoria
	primero y evitar problemas al reproducir.

	"""

	global rx_pipeline
	global play
	global buff_Rx

	if OPCODE == websocket.ABNF.OPCODE_TEXT:

		mensaje = json.loads(msg)
		event = mensaje["event"]

		if event == "ACK":
			data = mensaje["data"]
			print data

			print "¿Cúal es el nombre del mutante?"
			global mutant_name
			mutant_name = raw_input("--> ")

			print "¿Qué tipo de mutante eres? (T o R)"
			global mutant_type
			mutant_type = raw_input("--> ")
			while (mutant_type != "R") and (mutant_type != "T"):
				print "Error: Solo puede ser Transmisor (T) o Receptor (R)"
				mutant_type = raw_input("--> ")

			conn.send(json.dumps({"event": "clientInfo", "name": mutant_name, "type": mutant_type}))
			print "Enviada informacion del mutante {nombre: "+mutant_name+" tipo: "+mutant_type+" }"
			print "Esperando datos..."

		elif event == "envio":
			print "Escriba 'E' si desea compartir su audio con los receptores"

			respuesta = raw_input("--> ")
			while respuesta != "E":
				respuesta = raw_input("--> ")

			conn.send(json.dumps({"event": "initTx"}))
			send_audio(conn)

		elif event == "pausedTx":
			rx_pipeline.set_state(gst.State.PAUSED)
			print mensaje["data"]

		elif event == "resumeTx":
			rx_pipeline.set_state(gst.State.PLAYING)
			print mensaje["data"]

		elif event == "endTx":
			rx_pipeline.set_state(gst.State.NULL)
			play=0
			buff_Rx = None;
			buff_Rx = gio.MemoryInputStream()
			print mensaje["data"]


	elif OPCODE == websocket.ABNF.OPCODE_BINARY:

		if play == 20:
			buff_Rx.add_data(msg, None)
			play+=1
			gst_play = threading.Thread(target=player)
			gst_play.setDaemon(True)
			gst_play.start()

		else:
			buff_Rx.add_data(msg, None)
			if play < 20:
				play +=1

if __name__=="__main__":
	"""Función principal que lanza las distintas funciones.

	Primero pide la dirección IP del servidor y luego lanza la conexión por websockets.

	"""

	print "\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n"
	ip = raw_input("Indique la IP del servidor: ")
	SERVER = "ws://"+ip+":3000"

	#	Poner True si se desean ver las trazas y detectar posibles errores
	websocket.enableTrace(False)
	conn = websocket.WebSocketApp(SERVER,
								 on_message = on_message,
								 on_error = on_error,
								 on_close = on_close,
								 on_data = on_data)
	conn.on_open = on_open
	conn.run_forever()
