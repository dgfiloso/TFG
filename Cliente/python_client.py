#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""*************************************************************
*   @file       python_client.py
*   @version    2.3
*   @author     David González Filoso <dgfiloso@b105.upm.es>
*   @company    B105 Electronic Systems Lab
*   @description Cliente de Cerebro. Tiene opciones para elegir la
*				 dirección del servidor, el nombre y el tipo de
*				 cliente.
*************************************************************"""
import threading	#	Librería para usar distintas hebras
import json			#	Librería para usar objetos JSON
import subprocess	#	Librería para usar procesos del sistema
import sys			#	Librería para usar el sistema
try:
	import websocket 	#	Librería para usar websockets
except ImportError:
	print "#ERROR: websocket-client not installed"
	import pip
	pip.main(['install','--user','websocket-client'])
	print "Now websocket-client has been installed, execute the program"
	sys.exit()
#	Librerías de GStreamer
try:
	import gi
except ImportError:
	print "#ERROR: Gstreamer not installed"
	print "\t Execute 'sudo apt-get install gstreamer1.0 gstreamer1.0-*'"
	print "\t Execute 'sudo apt-get install python-gst-1.0'"
	sys.exit()

gi.require_version('Gst','1.0')
gi.require_version('Gtk','3.0')
from gi.repository import GObject, Gtk
from gi.repository import Gio as gio
from gi.repository import Gst as gst

import sys
try:
	from Tkinter import *
	import ttk
except ImportError:
    print "#ERROR: Tkinter not installed"
    print "Execute 'sudo apt-get install python-tk'"
    sys.exit()

OPCODE			= 1			#	Variable que guarda el valor del opcode del último mensaje
mutant_type 	= None		#	Variable que guarda el tipo de mutante del cliente
mutant_name 	= None		#	Variable que guarda el nombre del mutante
buff_Rx			= gio.MemoryInputStream()	#	Memoria que guarda los datos de entrada
tx_pipeline     = None		#	Variable que guarda el pipeline de transmisión
rx_pipeline 	= None		#	Variable que guarda el pipeline de recepción
play			= 0			#	Variable que se usa para esperar 20 paquetes antes de empezar a reproducir
conn			= None		#	Variable para guardar el socket del cliente
status			= None		#	Variable que guarda el estado del cliente

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
	# print "Reproduciendo..."
	global rx_pipeline, status

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

	status.set("Estado: RECEIVING")

	GObject.MainLoop().run()

def on_new_buffer(appsink):
	"""Enviamos los datos del pipeline de transmisión por los sockets.

	Esta función salta cuando el pipeline de transmisión emite una señal
	de tipo 'new-sample'. Se encarga de enviar esos datos a través de los sockets.

	appsink.emit('pull-sample') 					-> Devuelve un objeto de tipo Gst.Sample
	appsink.emit('pull-sample').get_buffer() 		-> Devuelve el Gst.Buffer de la muestra
	Gst.Buffer.extract_dup(0, tx_buffer.get_size()) -> Devuelve una copia de los datos desde el punto 0 hasta el punto indicado, en nuestro caso el tamaño total

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
	# print "Transmitiendo..."
	return False

def on_error(conn, err):
	"""Imprime errores de los sockets.

	"""
	print "Websocket connection Error: "+err

def on_close(conn):
	"""Informa del cierre de la conexión entre el socket y el servidor.

	"""
	# print "Cerrada conexion con el servidor"

def on_open(conn):
	"""Informa de la creación correcta del cliente.

	"""
	# print "\n\n\n\n"
	# print "Cliente creado..."
	if mutant_type == "R":
		app.show_frame(RxPage)
	elif mutant_type == "T":
		app.show_frame(TxPage1)

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
	-	pauseTx 	-- Pausa la reproducción del pipeline de recepción.
	-	resumeTx 	-- Continúa la reproducción del pipeline de recepción.
	-	endTx 		-- Finaliza la reproducción del pipeline de recepción.

	Cuando los datos recibidos son binarios, esperamos la llegada de varios paquetes,
	en nuestro caso 20, antes de comenzar a reproducir para llenar un poco la memoria
	primero y evitar problemas al reproducir.

	"""
	global rx_pipeline, play, buff_Rx

	if OPCODE == websocket.ABNF.OPCODE_TEXT:

		mensaje = json.loads(msg)
		event = mensaje["event"]

		if event == "ACK":
			data = mensaje["data"]
			# print data

			conn.send(json.dumps({"event": "clientInfo", "name": mutant_name, "type": mutant_type}))
			# print "Enviada informacion del mutante {nombre: "+mutant_name+" tipo: "+mutant_type+" }"

		elif event == "pauseTx":
			rx_pipeline.set_state(gst.State.PAUSED)
			# status.set("Estado: PAUSE")

		elif event == "resumeTx":
			rx_pipeline.set_state(gst.State.PLAYING)
			# status.set("Estado: RECEIVING")

		elif event == "endTx":
			rx_pipeline.set_state(gst.State.NULL)
			play=0
			buff_Rx = None;
			buff_Rx = gio.MemoryInputStream()
			# status.set("Estado: ENDED COMMUNICATION")


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

def cerebro_daemon(server_dir):
	"""Tarea que conecta con el servidor.

	Lanzamos la conexión con el servidor como una tarea concurrente para que no
	pare la ejecución de la parte gráfica.

	-	server_dir	-> Contiene la dirección del servidor

	"""
	global conn

	conn = websocket.WebSocketApp(server_dir,
								 on_message = on_message,
								 on_error = on_error,
								 on_close = on_close,
								 on_data = on_data)
	conn.on_open = on_open
	conn.run_forever()

class dgfGUI(Tk):
	"""Clase para la creación de la interfaz gráfica.

	Esta clase se encarga de lanzar las diferentes ventanas de la interfaz gráfica.

	"""

	def __init__(self, *args, **kwargs):
		"""Crea el contenedor de los posteriores frames de las interfaces.

		"""

		Tk.__init__(self, *args, **kwargs)

		container = Frame(self)

		container.pack(side="top",fill="both", expand=True)

		container.grid_rowconfigure(0, weight=1)
		container.grid_columnconfigure(0,weight=1)

		self.frames = {}

		for F in (StartPage, RxPage, TxPage1, TxPage2):

		    frame = F(container, self)

		    self.frames[F] = frame

		    frame.grid(row=0,column=0,sticky="nsew")

		self.show_frame(StartPage)

	def show_frame(self, cont):
		"""Muestra en la ventana el frame pasado como parámetro.

		-	cont	-> Frame que se quiere mostrar

		"""
		frame = self.frames[cont]
		frame.tkraise()

class StartPage(Frame):
	"""Clase con la página de inicio de la aplicación.

	"""

	def server_conn(self,controller,mut_type):
		"""Configura los parámetros para la conexión con el servidor y la lanza.

		"""
		global mutant_name, mutant_type

		server_dir = "ws://"+self.entry_ip.get()+":3000"
		mutant_name = self.entry_name.get()
		mutant_type = mut_type.get()
		app.title("Cliente de Cerebro - "+str(mutant_name))

		cer_conn = threading.Thread(target=lambda:cerebro_daemon(server_dir))
		cer_conn.setDaemon(True)
		cer_conn.start()

	def __init__(self, parent, controller):
		"""Crea el frame de la página de inicio.

		"""
		Frame.__init__(self, parent)

		self.label_ip = Label(self, text="IP de Cerebro")
		self.entry_ip = ttk.Entry(self)

		self.label_name = Label(self, text="Nombre del mutante")
		self.entry_name = ttk.Entry(self)

		self.label_type = Label(self, text="Tipo de mutante")
		mut_type = StringVar()
		self.radiobutton_R = Radiobutton(self, text="Receptor", variable=mut_type, value="R")
		self.radiobutton_T = Radiobutton(self, text="Transmisor", variable=mut_type, value="T")

		self.conn_button = ttk.Button(self, text="Conectar", command=lambda:self.server_conn(controller,mut_type))
		self.close_button = ttk.Button(self, text="Cerrar", command=parent.quit)

		self.label_ip.grid(row=0, column=0)
		self.entry_ip.grid(row=1, column=0)
		self.label_name.grid(row=0, column=1)
		self.entry_name.grid(row=1, column=1)
		self.label_type.grid(row=2, column=0, columnspan=2)
		self.radiobutton_R.grid(row=3, column=0)
		self.radiobutton_T.grid(row=3, column=1)
		self.conn_button.grid(row=4, column=0)
		self.close_button.grid(row=4, column=1)

		self.grid_rowconfigure(0,weight=1)
		self.grid_rowconfigure(1,weight=1)
		self.grid_rowconfigure(2,weight=1)
		self.grid_rowconfigure(3,weight=1)
		self.grid_rowconfigure(4,weight=1)
		self.grid_columnconfigure(0,weight=1)
		self.grid_columnconfigure(1,weight=1)

class RxPage(Frame):
	"""Clase con la página del receptor.

	"""

	def reboot(self,controller):
		"""Reinicia el cliente y vuelve a la página inicial.

		"""
		global rx_pipeline, play, buff_Rx, conn

		if rx_pipeline != None:
			rx_pipeline.set_state(gst.State.NULL)

		play=0
		buff_Rx = None;
		buff_Rx = gio.MemoryInputStream()
		conn.close()
		controller.show_frame(StartPage)

	def __init__(self, parent, controller):
		"""Crea el frame de la página del receptor.

		"""
		Frame.__init__(self, parent)

		global status
		status = StringVar()
		self.label_status = Label(self, textvariable=status)
		status.set("Estado: READY")
		self.reboot_button = ttk.Button(self, text="Reiniciar", command=lambda:self.reboot(controller))
		self.close_button = ttk.Button(self, text="Cerrar", command=parent.quit)

		self.label_status.grid(row=0, column=0, columnspan=2, sticky=NSEW)
		self.reboot_button.grid(row=1, column=0, sticky=NSEW)
		self.close_button.grid(row=1, column=1, sticky=NSEW)

		self.grid_rowconfigure(0,weight=2)
		self.grid_rowconfigure(1,weight=3)
		self.grid_columnconfigure(0,weight=1)
		self.grid_columnconfigure(1,weight=1)

class TxPage1(Frame):
	"""Clase con la primera página de los transmisores.

	En esta página se decide cuando se quiere comenzar a transmitir el audio.

	"""

	def send_audio(self, controller):
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
		# print "Numero del bus de la tarjeta de sonido: "+soundCard
		soundCard = soundCard.replace(":","_")

		# print "Vamos a ejecutar: "+'pacmd set-default-source alsa_output.'+soundCard+'.analog-stereo.monitor'
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

		controller.show_frame(TxPage2)

		tx_daemon = threading.Thread(target=lambda:GObject.MainLoop().run())
		tx_daemon.setDaemon(True)
		tx_daemon.start()

	def reboot(self,controller):
		"""Reinicia el cliente y vuelve a la página inicial.

		"""
		global tx_pipeline,conn

		if tx_pipeline != None:
			tx_pipeline.set_state(gst.State.NULL)
			tx_pipeline = None

		conn.close()
		controller.show_frame(StartPage)

	def __init__(self, parent, controller):
		"""Crea la primera página del transmisor.

		"""
		Frame.__init__(self, parent)

		self.tx_button = ttk.Button(self, text="Transmitir", command=lambda:self.send_audio(controller))
		self.reboot_button = ttk.Button(self, text="Reiniciar", command=lambda:self.reboot(controller))
		self.stop_button = ttk.Button(self, text="Cerrar", command=parent.quit)

		self.tx_button.grid(row=0, column=0, sticky=NSEW)
		self.reboot_button.grid(row=1, column=0, sticky=NSEW)
		self.stop_button.grid(row=2, column=0, sticky=NSEW)

		self.grid_rowconfigure(0,weight=3)
		self.grid_rowconfigure(1,weight=1)
		self.grid_rowconfigure(2,weight=1)
		self.grid_columnconfigure(0,weight=2)

class TxPage2(Frame):
	"""Clase con la segunda página del transmisor.

	En esta página ya se permite controlar la tranmisión.

	"""

	def pauseTx(self):
		"""Pausa la transmisión.

		"""
		conn.send(json.dumps({"event": "pauseTx", "data": "PAUSE"}))
		tx_pipeline.set_state(gst.State.PAUSED)
		status.set("Estado: PAUSE")

	def resumeTx(self):
		"""Reanuda la transmisión.

		"""
		conn.send(json.dumps({"event": "resumeTx", "data": "RESUME"}))
		tx_pipeline.set_state(gst.State.PLAYING)
		status.set("Estado: TRANSMITTING")

	def endTx(self):
		"""Finaliza la transmisión.

		"""
		conn.send(json.dumps({"event": "endTx", "data": "ENDED COMMUNICATION"}))
		tx_pipeline.set_state(gst.State.NULL)
		sys.exit();

	def reboot(self,controller):
		"""Reinicia el cliente y vuelve a la página inicial.

		"""
		global tx_pipeline,conn

		if tx_pipeline != None:
			tx_pipeline.set_state(gst.State.NULL)
			tx_pipeline = None

		conn.close()
		controller.show_frame(StartPage)

	def __init__(self, parent, controller):
		"""Crea la segunda página del transmisor.

		"""
		Frame.__init__(self, parent)

		global status
		status = StringVar()
		self.label_status = Label(self, textvariable=status)
		status.set("Estado: TRANSMITTING")
		self.resume_button = ttk.Button(self, text="Reanudar", command=lambda:self.resumeTx())
		self.pause_button = ttk.Button(self, text="Pausar", command=lambda:self.pauseTx())
		self.reboot_button = ttk.Button(self, text="Reiniciar", command=lambda:self.reboot(controller))
		self.stop_button = ttk.Button(self, text="Detener y Cerrar", command=lambda:self.endTx())

		self.label_status.grid(row=0, column=0, columnspan=2)
		self.resume_button.grid(row=1, column=0, sticky=NSEW)
		self.pause_button.grid(row=1, column=1, sticky=NSEW)
		self.reboot_button.grid(row=2, column=0, sticky=NSEW)
		self.stop_button.grid(row=2, column=1, sticky=NSEW)

		self.grid_rowconfigure(0,weight=1)
		self.grid_rowconfigure(1,weight=2)
		self.grid_rowconfigure(2,weight=2)
		self.grid_columnconfigure(0,weight=1)
		self.grid_columnconfigure(1,weight=1)


if __name__=="__main__":
	"""Función principal que lanza las distintas funciones.

	Lanza el objeto de GStreamer y la interfaz gráfica. Además en función de los
	argumentos que se le pase al llamar al programa, se pueden activar las trazas
	de depuración.

	"""
	GObject.threads_init()
	gst.init(None)

	if len(sys.argv) > 2:
		print "#ERROR: Máximo un argumento"
		print "Use --help para más informacion"
		sys.exit()
	elif len(sys.argv) == 1:
		websocket.enableTrace(False)
	else:
		if sys.argv[1] == '--help':
			print "Si quiere activar las trazas del programa use los siguientes argumentos:"
			print "--DEBUG=G -> Para activar las trazas de GStreamer"
			print "--DEBUG=W -> Para activar las trazas de Websocket"
			print "--DEBUG=A -> Para activar todas las trazas"
			sys.exit()
		elif sys.argv[1] == '--DEBUG=G':
			gst.debug_set_active(True)
			gst.debug_set_default_threshold(3)
			websocket.enableTrace(False)
		elif sys.argv[1] == '--DEBUG=W':
			websocket.enableTrace(True)
		elif sys.argv[1] == '--DEBUG=A':
			gst.debug_set_active(True)
			gst.debug_set_default_threshold(3)
			websocket.enableTrace(True)
		else:
			print "#ERROR: Argumento no valido"
			sys.exit()

	app = dgfGUI()
	app.title("Cliente de Cerebro")
	app.mainloop()
