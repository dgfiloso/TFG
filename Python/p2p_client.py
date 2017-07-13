#!/usr/bin/python
# -*- coding: utf-8 -*-
"""*************************************************************
*   @file       p2p_client.py
*   @version    3.0
*   @author     David González Filoso <dgfiloso@b105.upm.es>
*   @company    B105 Electronic Systems Lab
*   @description Transmisor/Receptor del sistema Cerebro
*************************************************************"""
import threading  	# Librería para usar distintas hebras
import json  		# Librería para usar objetos JSON
import subprocess  	# Librería para usar procesos del sistema
import sys  		# Librería para usar el sistema
import socket  		# Librería para usar sockets
import struct  		# Librería para usar estructuras como en C
import string		# Librería para usar operaciones con strings

#	Librerías de GStreamer
try:
	import gi
except ImportError:
	print "#ERROR: Gstreamer not installed"
	print "\t Execute 'sudo apt-get install gstreamer1.0 gstreamer1.0-*'"
	print "\t Execute 'sudo apt-get install python-gst-1.0'"
	sys.exit()

gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, Gtk
from gi.repository import Gio as gio
from gi.repository import Gst as gst

#	Librería de Tkinter
try:
	from Tkinter import *
	import tkMessageBox
	import ttk
except ImportError:
	print "#ERROR: Tkinter not installed"
	print "Execute 'sudo apt-get install python-tk'"
	sys.exit()

DISCOVERY_ADDR 	= '239.11.11.11'  	# Dirección del grupo multicast por donde hacemos el descubrimiento
DISCOVERY_PORT 	= 3000  			# Puerto del grupo multicast por donde hacemos el descubrimiento
discovery_task 	= None				# Tarea que escucha mensajes de descubrimiento
discovery_sock	= None				# Socket de descubrimiento
mutant_ip 		= None  			# Dirección ip del mutante
mutant_type 	= None  			# Tipo de mutante del cliente
mutant_name 	= None  			# Nombre del mutante
buff_Rx = gio.MemoryInputStream()  	# Datos de entrada
tx_pipeline 	= None  			# Pipeline de transmisión
rx_pipeline 	= None  			# Pipeline de recepción
play 			= 0  				# Variable que se usa para esperar 20 paquetes antes de empezar a reproducir
tcp_conn 		= None  			# Socket TCP
udp_addr 		= None  			# Dirección para comunicación UDP
recv_udp 		= 1  				# Indica si tenemos que recibir (0) o no (1) paquetes UDP
status 			= None  			# Estado del cliente

def discovery():
	"""Servidor que escucha mensajes de descubrimiento para enviar la información del mutante.

	Esta función se encarga de crear un socket UDP y unirlo al grupo multicast 239.11.11.11:30000 que es
	el que usaremos para enviar mensajes de descubrimiento. Al recibir un mensaje de descubrimiento envía
	su nombre, tipo y su IP.

	"""
	global discovery_sock
	#   Create the datagram socket
	discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	#   Bind to the server address
	discovery_sock.bind((DISCOVERY_ADDR, DISCOVERY_PORT))

	# Tell the operating system to add the socket to the multicast group
	# on all interfaces.
	group = socket.inet_aton(DISCOVERY_ADDR)
	mreq = struct.pack('4sL', group, socket.INADDR_ANY)
	discovery_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

	#   Set the TTL for the messages to 1 so they do not go past the local network segment.
	ttl = struct.pack('b', 1)
	discovery_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

	# Receive/respond loop
	while True:
		data, address = discovery_sock.recvfrom(32)
		ip, port = address
		if data[0] == "\x11":
			if data[1:11] == "DiscoverTx" and mutant_type == 'T' and udp_addr != None:
				msg = "\x11%s" % (json.dumps({"name": mutant_name, "type": mutant_type, "address": udp_addr}))
				discovery_sock.sendto(msg, address)

			elif data[1:9] == "Discover":
				msg = "\x11%s" % (json.dumps({"name": mutant_name, "type": mutant_type, "address": mutant_ip}))
				discovery_sock.sendto(msg, address)



class mutantGUI(Tk):
	"""Clase para la creación de la interfaz gráfica.

	Esta clase se encarga de lanzar las diferentes ventanas de la interfaz gráfica.

	"""

	def __init__(self, *args, **kwargs):
		"""Crea el contenedor de los posteriores frames de las interfaces.

		"""
		Tk.__init__(self, *args, **kwargs)

		container = Frame(self)

		container.pack(side="top", fill="both", expand=True)

		container.grid_rowconfigure(0, weight=1)
		container.grid_columnconfigure(0, weight=1)

		self.frames = {}

		for F in (StartPage, RxPage, TxPage, AdminPage):
			frame = F(container, self)

			self.frames[F] = frame

			frame.grid(row=0, column=0, sticky="nsew")

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

	def mutant_conn(self, controller, mut_type):
		"""Configura los parámetros del mutante.

		"""
		global mutant_name, mutant_type, discovery_task

		mutant_name = self.entry_name.get()
		mutant_type = mut_type.get()
		app.title("Cliente de Cerebro - " + str(mutant_name))

		discovery_task = threading.Thread(target=discovery)
		discovery_task.setDaemon(True)
		discovery_task.start()

		if mutant_type == "R":
			app.show_frame(RxPage)
		elif mutant_type == "T":
			app.show_frame(TxPage)

	def admin(self, controller):
		"""Lanza el panel de administración de todos los mutantes.

		"""
		app.title("Administración mutantes de Cerebro")
		app.show_frame(AdminPage)

	def __init__(self, parent, controller):
		"""Crea el frame de la página de inicio.

		"""
		Frame.__init__(self, parent)

		self.label_name = Label(self, text="Nombre del mutante")
		self.entry_name = ttk.Entry(self)

		self.label_type = Label(self, text="Tipo de mutante")
		mut_type = StringVar()
		self.radiobutton_R = Radiobutton(self, text="Receptor", variable=mut_type, value="R")
		self.radiobutton_T = Radiobutton(self, text="Transmisor", variable=mut_type, value="T")

		self.conn_button = ttk.Button(self, text="Conectar", command=lambda: self.mutant_conn(controller, mut_type))
		self.admin_button = ttk.Button(self, text="Administrar", command=lambda: self.admin(controller))
		self.close_button = ttk.Button(self, text="Cerrar", command=parent.quit)

		self.label_name.grid(row=0, column=0, columnspan=3)
		self.entry_name.grid(row=1, column=0, columnspan=3)
		self.label_type.grid(row=2, column=0, columnspan=3)
		self.radiobutton_R.grid(row=3, column=0)
		self.radiobutton_T.grid(row=3, column=2)
		self.conn_button.grid(row=4, column=0)
		self.admin_button.grid(row=4, column=1)
		self.close_button.grid(row=4, column=2)

		self.grid_rowconfigure(0, weight=1)
		self.grid_rowconfigure(1, weight=1)
		self.grid_rowconfigure(2, weight=1)
		self.grid_rowconfigure(3, weight=1)
		self.grid_rowconfigure(4, weight=1)
		self.grid_columnconfigure(0, weight=1)
		self.grid_columnconfigure(1, weight=1)
		self.grid_columnconfigure(2, weight=1)


class RxPage(Frame):
	"""Clase con la página del receptor.

	"""
	def player(self):
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

		audio_src = gst.ElementFactory.make("giostreamsrc", "audio_src")
		decode = gst.ElementFactory.make("mad", "decode")
		convert = gst.ElementFactory.make("audioconvert", "convert")
		audio_sink = gst.ElementFactory.make("pulsesink", "audio_sink")

		audio_src.set_property('stream', buff_Rx)

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

	def udp_rx(self):
		"""Crea una conexión UDP para recibir el contenido multimedia.

		Esta función primero conecta el socket UDP con la dirección udp_addr
		y luego entra en un bucle que va llenando el buffer que GStreamer va
		a ir reproduciendo

		"""
		global play, buff_Rx

		self.udp_conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		try:
			self.udp_conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		except AttributeError:
			pass
		self.udp_conn.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
		self.udp_conn.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)

		self.udp_conn.bind((udp_addr, 3000))
		host = socket.gethostbyname(socket.gethostname())
		self.udp_conn.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(host))
		self.udp_conn.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP,
							socket.inet_aton(udp_addr) + socket.inet_aton(host))

		while (1):
			if recv_udp == 0:
				msg, addr = self.udp_conn.recvfrom(1024)
				if play == 20:
					buff_Rx.add_data(msg, None)
					play += 1
					gst_play = threading.Thread(target=lambda: self.player())
					gst_play.setDaemon(True)
					gst_play.start()

				else:
					buff_Rx.add_data(msg, None)
					if play < 20:
						play += 1

			elif recv_udp == 2:
				break

	def conexiones(self, socket_cliente):
		"""Recibe los mensajes de un socket TCP y los interpreta.

		Primero revisa si la cabecera es la correcta, 0x11, y después lee el resto
		del mensaje. Diferencia entre distintos eventos:

		- udpRx : Indica la dirección del grupo multicast al que hay que conectarse.
		- pauseTx : Indica que la comunicación se ha parado.
		- resumeTx : Indica que la comunicación se reanuda.
		- endTx : Indica que la comunicación ha finalizado completamente.

		"""

		global rx_pipeline, play, buff_Rx, udp_addr, recv_udp

		while 1:
			cabecera = socket_cliente.recv(1)
			if cabecera == '\x11':
				len_length = int(socket_cliente.recv(1))
				print "[*] Longitud del campo longitud: %d" % (len_length)
				length = int(socket_cliente.recv(len_length))
				print "[*] Longitud del mensaje recibido: %s" % length
				data = socket_cliente.recv(length)
				rx_msg = json.loads(data)
				event = rx_msg["event"]

				if event == "udpRx":
					udp_addr = rx_msg["data"]
					print "UDP_RX on " + udp_addr
					recv_udp = 0
					udp_listener = threading.Thread(target=lambda: self.udp_rx())
					udp_listener.setDaemon(True)
					udp_listener.start()

				elif event == "pauseTx":
					recv_udp = 1
					rx_pipeline.set_state(gst.State.PAUSED)

				elif event == "resumeTx":
					recv_udp = 0
					rx_pipeline.set_state(gst.State.PLAYING)

				elif event == "endTx":
					recv_udp = 2
					rx_pipeline.set_state(gst.State.NULL)
					play = 0
					buff_Rx = None
					buff_Rx = gio.MemoryInputStream()

				elif event == "delete":
					sys.exit()

		socket_cliente.close()

	def mutant_listen(self, servidor, puerto):
		"""Servidor TCP que escucha conexiones por el puerto 3000.

		Cada vez que se conecta un socket, se crea una hebra para escuchar sus mensajes.

		"""
		print "[*] Esperando conexiones en %s:%d" % (mutant_ip, puerto)

		while True:
			cliente, direccion = servidor.accept()
			print "[*] Conexion establecida con %s:%d" % (direccion[0], direccion[1])
			conn = threading.Thread(target=lambda: self.conexiones(cliente))
			conn.setDaemon(True)
			conn.start()

	def recv_audio(self):
		"""Crea el socket y lo conecta al grupo multicast que se le ha indicado para recibir el audio.

		"""

		self.recv_button.destroy()

		self.label_status.grid(row=0, column=0, columnspan=2, sticky=NSEW)
		self.reboot_button.grid(row=1, column=0, sticky=NSEW)
		self.close_button.grid(row=1, column=1, sticky=NSEW)

		self.grid_rowconfigure(0, weight=2)
		self.grid_rowconfigure(1, weight=3)
		self.grid_columnconfigure(0, weight=1)
		self.grid_columnconfigure(1, weight=1)

		global status, tcp_conn

		puerto = 3000
		max_conexiones = 5
		tcp_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		tcp_conn.bind((mutant_ip, puerto))
		tcp_conn.listen(max_conexiones)

		status.set("Estado: READY")

		listen_t = threading.Thread(target=lambda: self.mutant_listen(tcp_conn, puerto))
		listen_t.setDaemon(True)
		listen_t.start()

	def reboot(self, controller):
		"""Reinicia el cliente y vuelve a la página inicial.

		"""
		global rx_pipeline, play, buff_Rx, tcp_conn, discovery_sock

		if rx_pipeline != None:
			rx_pipeline.set_state(gst.State.NULL)

		play = 0
		buff_Rx = None;
		buff_Rx = gio.MemoryInputStream()

		if tcp_conn != None:
			tcp_conn.close()
			tcp_conn = None

		discovery_sock.close()
		if self.udp_conn != None:
			self.udp_conn.close()

		controller.show_frame(StartPage)

	def close(self, parent):
		"""Cierra el programa.

		"""
		global tcp_conn, discovery_sock

		if tcp_conn != None:
			tcp_conn.close()
			tcp_conn = None

		discovery_sock.close()

		if self.udp_conn != None:
			self.udp_conn.close()

		parent.quit()

	def __init__(self, parent, controller):
		"""Crea el frame de la página del receptor.

		"""
		Frame.__init__(self, parent)

		global status
		self.udp_conn = None

		status = StringVar()
		self.label_status = Label(self, textvariable=status)
		status.set("Estado: STOP")
		self.recv_button = ttk.Button(self, text="Recibir", command=lambda: self.recv_audio())
		self.reboot_button = ttk.Button(self, text="Reiniciar", command=lambda: self.reboot(controller))
		self.close_button = ttk.Button(self, text="Cerrar", command=lambda: self.close(parent))

		self.label_status.grid(row=0, column=0, columnspan=2, sticky=NSEW)
		self.recv_button.grid(row=1, column=0, columnspan=2, sticky=NSEW)
		self.reboot_button.grid(row=2, column=0, sticky=NSEW)
		self.close_button.grid(row=2, column=1, sticky=NSEW)

		self.grid_rowconfigure(0, weight=2)
		self.grid_rowconfigure(1, weight=3)
		self.grid_rowconfigure(2, weight=3)
		self.grid_columnconfigure(0, weight=1)
		self.grid_columnconfigure(1, weight=1)


class TxPage(Frame):
	"""Clase con la página de los transmisores.

	En esta página se decide cuando se quiere comenzar a transmitir el audio.

	"""

	def on_new_buffer(self, appsink):
		"""Enviamos los datos del pipeline de transmisión por los sockets.

		Esta función salta cuando el pipeline de transmisión emite una señal
		de tipo 'new-sample'. Se encarga de enviar esos datos a través de los sockets.

		appsink.emit('pull-sample') 					-> Devuelve un objeto de tipo Gst.Sample
		appsink.emit('pull-sample').get_buffer() 		-> Devuelve el Gst.Buffer de la muestra
		Gst.Buffer.extract_dup(0, tx_buffer.get_size()) -> Devuelve una copia de los datos desde el punto 0 hasta el punto indicado, en nuestro caso el tamaño total

		"""
		tx_buffer = appsink.emit('pull-sample').get_buffer()
		tx_data = tx_buffer.extract_dup(0, tx_buffer.get_size())
		self.udp_conn.sendto(tx_data, (udp_addr, 3000))
		return False

	def on_new_preroll(self, appsink):
		"""Indica que vamos a empezar a transmisitir.

		Esta función salta cuando el pipeline de transmisión emite una señal
		de tipo 'new-preroll'. Se encarga de avisar de que vamos a comenzar a
		transmitir.

		Los datos de preroll son datos de control, siempre salta uno antes de
		transmitir, por ello lo utilizamos para avisar al usuario.

		"""
		# print "Transmitiendo..."
		return False

	def conexiones(self, socket_cliente):
		"""Recibe los mensajes de un socket TCP y los interpreta.

		Recibe un array con los receptores que se tienen que conectar a él.
		Después se va conectando a ellos y les envía el mensaje udpRx con el
		grupo multicast en el que está transmitiendo.

		"""
		while 1:
			cabecera = socket_cliente.recv(1)
			if cabecera == '\x11':
				len_length = int(socket_cliente.recv(1))
				print "[*] Longitud del campo longitud: %d" % (len_length)
				length = int(socket_cliente.recv(len_length))
				print "[*] Longitud del mensaje recibido: %s" % length
				data = socket_cliente.recv(length)
				rx_msg = json.loads(data)
				self.rx_list = rx_msg['rx']
				print "[*] Receptores conectados: %s" % self.rx_list

				json_msg = json.dumps({"event": "udpRx", "data": udp_addr})
				if len(json_msg) < 255:
					len_length = 0
					if len(json_msg) < 10:
						len_length = 1
					elif len(json_msg) < 100:
						len_length = 2
					else:
						len_length = 2

					msg = "\x11%d%d%s" % (len_length, len(json_msg), json_msg)

					for recv in self.rx_list:
						print "Conectamos con %s" % recv
						control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
						control.connect((recv, 3000))
						control.send(msg)
						print "Enviado: %s a %s:3000" % (msg, recv)
						control.close()

				else:
					print "#ERROR: Message too long"

		socket_cliente.close()

	def tx_listen(self, servidor, puerto):
		"""Servidor TCP que escucha conexiones por el puerto 3000.

		Cada vez que se conecta un socket, se crea una hebra para escuchar sus mensajes.

		"""
		print "[*] Esperando conexiones en %s:%d" % (mutant_ip, puerto)

		while True:
			cliente, direccion = servidor.accept()
			print "[*] Conexion establecida con %s:%d" % (direccion[0], direccion[1])
			conn = threading.Thread(target=lambda: self.conexiones(cliente))
			conn.setDaemon(True)
			conn.start()

	def send_audio(self, controller):
		"""Tomamos el audio del sistema y lo transmitimos mediante sockets.

		Esta función se puede dividir en cinco partes claras:

		1. 	Cambiamos los widgets del frame.

		2. 	Busca una dirección multicast libre.

		3. 	Lanza un servidor tcp que se encarga de recibir las direcciones IP de los
			receptores que se van a conectar a él.

		4.	Buscamos el número de nuestra tarjeta de sonido y cambiamos la entrada
			de audio a 'Monitor of' para crear un enlace entre los altavoces y
			el micrófono.

		5.	Creamos un pipeline de transmisión que lee el micrófono y envía sus
			datos mediante sockets.

		Elementos del pipeline de transmisión:

		-	pulsesrc		-- Lee los datos del micrófono
		-	audioconvert	-- Elemento usado para la conversión
		-	lamemp3enc		-- Convierte los datos del micrófono a MP3
		-	appsink			-- Elemento utilizado para obtener los datos y transmitirlos

		"""
		#	******* 1. Cambiamos la interfaz
		self.tx_button.destroy()

		global status
		status = StringVar()
		self.label_status = Label(self, textvariable=status)
		status.set("Estado: TRANSMITTING")
		self.resume_button = ttk.Button(self, text="Reanudar", command=lambda: self.resumeTx())
		self.pause_button = ttk.Button(self, text="Pausar", command=lambda: self.pauseTx())
		self.reboot_button = ttk.Button(self, text="Reiniciar", command=lambda: self.reboot(controller))
		self.stop_button = ttk.Button(self, text="Detener y Cerrar", command=lambda: self.endTx())

		self.label_status.grid(row=0, column=0, columnspan=2)
		self.resume_button.grid(row=1, column=0, sticky=NSEW)
		self.pause_button.grid(row=1, column=1, sticky=NSEW)
		self.reboot_button.grid(row=2, column=0, sticky=NSEW)
		self.stop_button.grid(row=2, column=1, sticky=NSEW)

		self.grid_rowconfigure(0, weight=1)
		self.grid_rowconfigure(1, weight=2)
		self.grid_rowconfigure(2, weight=2)
		self.grid_columnconfigure(0, weight=1)
		self.grid_columnconfigure(1, weight=1)

		#	******* 2. Buscamos una dirección multicast libre
		global udp_addr
		#   Create the datagram socket
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		# Tell the operating system to add the socket to the multicast group
		# on all interfaces.
		group = socket.inet_aton(DISCOVERY_ADDR)
		mreq = struct.pack('4sL', group, socket.INADDR_ANY)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

		#   Set the TTL for the messages to 1 so they do not go past the local network segment.
		ttl = struct.pack('b', 1)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

		# Set a timeout so the socket does not block indefinitely when trying
		# to receive data.
		sock.settimeout(1)

		tx_addr_taken = []

		tkMessageBox.showinfo("Transmisión", "Configurando dirección para transmitir...")

		try:
			# Send data to the multicast group
			sent = sock.sendto('\x11DiscoverTx', (DISCOVERY_ADDR, DISCOVERY_PORT))
			# Look for responses from all recipients
			while True:
				try:
					data, address = sock.recvfrom(256)
					ip, port = address
				except socket.timeout:
					break
				else:
					if ip != mutant_ip and data[0] == "\x11":
						print "%s from %s:%d" % (data, ip, port)
						info = json.loads(data[1:63])
						m_type = info["type"]
						m_addr = info["address"]
						if m_type == 'T':
							tx_addr_taken.append(m_addr)

		finally:
			sock.close()
			udp_addr = "239.11.11.12"
			translation = string.maketrans('0123456789', '1234567890')
			while 1:
				try:
					tx_index = tx_addr_taken.index(udp_addr)
				except ValueError:
					break
				else:
					udp_addr = list(udp_addr)
					udp_addr[len(udp_addr) - 1] = string.translate(udp_addr[len(udp_addr) - 1], translation)
					if udp_addr[len(udp_addr) - 1] == 0:
						udp_addr[len(udp_addr) - 2] = string.translate(udp_addr[len(udp_addr) - 2], translation)

					udp_addr = ''.join(udp_addr)

			print "Dirección de transmisión: %s" % udp_addr
			self.udp_conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
			self.udp_conn.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)

		# ******* 3. Lanzamos el servidor TCP
		global tcp_conn
		puerto = 3000
		max_conexiones = 1
		tcp_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		tcp_conn.bind((mutant_ip, puerto))
		tcp_conn.listen(max_conexiones)

		listen_t = threading.Thread(target=lambda: self.tx_listen(tcp_conn, puerto))
		listen_t.setDaemon(True)
		listen_t.start()

		#	******* 4. Buscamos el número de nuestra tarjeta de sonido
		p = subprocess.Popen(['pacmd', 'list-cards'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		g = subprocess.Popen(['grep', 'device.bus_path'], stdin=p.stdout, stdout=subprocess.PIPE,
							 stderr=subprocess.STDOUT)
		soundCard = g.stdout.read().split('"')[1]
		# print "Numero del bus de la tarjeta de sonido: "+soundCard
		soundCard = soundCard.replace(":", "_")

		# print "Vamos a ejecutar: "+'pacmd set-default-source alsa_output.'+soundCard+'.analog-stereo.monitor'
		subprocess.call(['pacmd', 'set-default-source', 'alsa_output.' + soundCard + '.analog-stereo.monitor'])

		#	******* 5. Creamos un pipeline de transmisión y comenzamos a transmitir
		global tx_pipeline

		#	Implementación con GStreamer
		tx_pipeline = gst.Pipeline()

		audio_src = gst.ElementFactory.make("pulsesrc", "audio_src")
		convert = gst.ElementFactory.make("audioconvert", "convert")
		encoder = gst.ElementFactory.make("lamemp3enc", "encoder")
		audio_sink = gst.ElementFactory.make("appsink", "audio_sink")

		audio_sink.set_property('emit-signals', True)  # Permite emitir las señales 'new-sample' y 'new-preroll'
		audio_sink.set_property('sync', False)  # Hace la decodificacion lo mas rapida posible
		audio_sink.connect('new-sample', self.on_new_buffer)
		audio_sink.connect('new-preroll', self.on_new_preroll)

		tx_pipeline.add(audio_src)
		tx_pipeline.add(convert)
		tx_pipeline.add(encoder)
		tx_pipeline.add(audio_sink)

		audio_src.link(convert)
		convert.link(encoder)
		encoder.link(audio_sink)

		tx_pipeline.set_state(gst.State.PLAYING)

		tx_daemon = threading.Thread(target=lambda: GObject.MainLoop().run())
		tx_daemon.setDaemon(True)
		tx_daemon.start()

	def pauseTx(self):
		"""Pausa la transmisión.

		"""
		control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		json_msg = json.dumps({"event": "pauseTx", "data": "PAUSE"})
		if len(json_msg) < 255:
			len_length = 0
			if len(json_msg) < 10:
				len_length = 1
			elif len(json_msg) < 100:
				len_length = 2
			else:
				len_length = 2

			msg = "\x11%d%d%s" % (len_length, len(json_msg), json_msg)

			for i in range(0, len(self.rx_list)):
				control.connect((self.rx_list[i], 3000))
				control.send(msg)
				control.close()

			tx_pipeline.set_state(gst.State.PAUSED)
			status.set("Estado: PAUSE")

		else:
			print "#ERROR: Message too long"

	def resumeTx(self):
		"""Reanuda la transmisión.

		"""
		control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		json_msg = json.dumps({"event": "resumeTx", "data": "RESUME"})
		if len(json_msg) < 255:
			len_length = 0
			if len(json_msg) < 10:
				len_length = 1
			elif len(json_msg) < 100:
				len_length = 2
			else:
				len_length = 2

			msg = "\x11%d%d%s" % (len_length, len(json_msg), json_msg)

			for i in range(0, len(self.rx_list)):
				control.connect((self.rx_list[i], 3000))
				control.send(msg)
				control.close()

			tx_pipeline.set_state(gst.State.PLAYING)
			status.set("Estado: TRANSMITTING")

		else:
			print "#ERROR: Message too long"

	def endTx(self):
		"""Finaliza la transmisión.

		"""
		control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		json_msg = json.dumps({"event": "endTx", "data": "ENDED COMMUNICATION"})
		if len(json_msg) < 255:
			len_length = 0
			if len(json_msg) < 10:
				len_length = 1
			elif len(json_msg) < 100:
				len_length = 2
			else:
				len_length = 2

			msg = "\x11%d%d%s" % (len_length, len(json_msg), json_msg)

			for i in range(0, len(self.rx_list)):
				control.connect((self.rx_list[i], 3000))
				control.send(msg)
				control.close()

			tx_pipeline.set_state(gst.State.NULL)
			if (self.udp_conn != None):
				self.udp_conn.close()
			sys.exit()

		else:
			print "#ERROR: Message too long"

	def reboot(self, controller):
		"""Reinicia el cliente y vuelve a la página inicial.

		"""
		global tx_pipeline, tcp_conn, discovery_sock

		if tx_pipeline != None:
			tx_pipeline.set_state(gst.State.NULL)
			tx_pipeline = None

		if tcp_conn != None:
			tcp_conn.close()
			tcp_conn = None

		discovery_sock.close()

		if (self.udp_conn != None):
			self.udp_conn.close()
		controller.show_frame(StartPage)

	def close(self, parent, controller):
		"""Cierra el programa.

		"""
		global tcp_conn, discovery_sock

		if tcp_conn != None:
			tcp_conn.close()
			tcp_conn = None

		discovery_sock.close()

		if (self.udp_conn != None):
			self.udp_conn.close()
		parent.quit()

	def __init__(self, parent, controller):
		"""Crea la página del transmisor.

		"""
		Frame.__init__(self, parent)

		self.udp_conn = None  # Socket UDP
		self.rx_list = []  # Receptores conectados

		self.tx_button = ttk.Button(self, text="Transmitir", command=lambda: self.send_audio(controller))
		self.reboot_button = ttk.Button(self, text="Reiniciar", command=lambda: self.reboot(controller))
		self.stop_button = ttk.Button(self, text="Cerrar", command=lambda: self.close(parent, controller))

		self.tx_button.grid(row=0, column=0, sticky=NSEW)
		self.reboot_button.grid(row=1, column=0, sticky=NSEW)
		self.stop_button.grid(row=2, column=0, sticky=NSEW)

		self.grid_rowconfigure(0, weight=3)
		self.grid_rowconfigure(1, weight=1)
		self.grid_rowconfigure(2, weight=1)
		self.grid_columnconfigure(0, weight=2)


class AdminPage(Frame):
	"""Clase que permite conectar unos mutantes con otros.

	"""

	def mutant_discovery(self, parent, controller):
		"""Manda un mensaje por la dirección de descubrimiento para que le manden información.

		"""
		#   Create the datagram socket
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		# Tell the operating system to add the socket to the multicast group
		# on all interfaces.
		group = socket.inet_aton(DISCOVERY_ADDR)
		mreq = struct.pack('4sL', group, socket.INADDR_ANY)
		self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

		#   Set the TTL for the messages to 1 so they do not go past the local network segment.
		ttl = struct.pack('b', 1)
		self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

		# Set a timeout so the socket does not block indefinitely when trying
		# to receive data.
		self.sock.settimeout(1)

		tx_list = []
		rx_list = []

		tkMessageBox.showinfo("Descubrimiento", "Buscando mutantes en la red...")

		try:
			# Send data to the multicast group
			sent = self.sock.sendto(('\x11Discover'), (DISCOVERY_ADDR, DISCOVERY_PORT))
			# Look for responses from all recipients
			while True:
				try:
					data, address = self.sock.recvfrom(256)
					ip, port = address
					print "%s from %s:%d" % (data, ip, port)
				except socket.timeout:
					break
				else:
					if data[0] == "\x11":
						info = json.loads(data[1:63])
						m_name = info["name"]
						m_type = info["type"]
						m_addr = info["address"]
						if m_type == 'T':
							tx_list.append([m_type, m_name, m_addr])
						elif m_type == 'R':
							rx_list.append([m_type, m_name, m_addr])

		finally:
			# sock.close()
			tx_row = 1
			rx_row = 1
			tx = StringVar()
			rx = []
			max_row = max([len(tx_list), len(rx_list)])
			print "Nº Tx: %d Nº Rx: %d Máximo filas: %d" % (len(tx_list), len(rx_list), max_row)
			while len(tx_list) > 0:
				button = Radiobutton(self, text=tx_list[tx_row-1][1], variable=tx, value=tx_list[tx_row-1][2])
				button.grid(row=tx_row, column=0)
				self.mutant_buttons.append(button)
				if tx_row == len(tx_list):
					break
				else:
					tx_row += 1
			while len(rx_list) > 0:
				rx.append(StringVar())
				button = Radiobutton(self, text=rx_list[rx_row-1][1], variable=rx[rx_row-1], value=rx_list[rx_row-1][2])
				button.grid(row=rx_row, column=1)
				self.mutant_buttons.append(button)
				if rx_row == len(rx_list):
					break
				else:
					rx_row += 1

			self.conn_button = ttk.Button(self, text="Conectar", command=lambda: self.send_audio(controller, tx, rx))

			self.label_tx.grid(row=0, column=0)
			self.label_rx.grid(row=0, column=1)
			self.discover_button.grid(row=max(tx_row, rx_row) + 1, column=0, columnspan=1, sticky=NSEW)
			self.conn_button.grid(row=max(tx_row, rx_row) + 1, column=1, sticky=NSEW)
			self.return_button.grid(row=max(tx_row, rx_row) + 2, column=0, sticky=NSEW)
			self.stop_button.grid(row=max(tx_row, rx_row) + 2, column=1, sticky=NSEW)

			self.grid_rowconfigure(0, weight=1)
			for j in range(1, max(tx_row, rx_row) + 2):
				self.grid_rowconfigure(j, weight=1)

			self.grid_columnconfigure(0, weight=2)
			self.grid_columnconfigure(1, weight=2)

	def send_audio(self, controller, tx, rx):
		"""Se conecta al transmisor elegido y le envía las direcciones IP de los receptores que se han seleccionado.

		"""
		print tx
		print rx
		if tx == None and rx == []:
			tkMessageBox.showinfo("Descubrimiento", "No se han elegido mutantes")
		elif tx == None:
			tkMessageBox.showinfo("Descubrimiento", "No se ha elegido transmisor")
		elif rx == []:
			tkMessageBox.showinfo("Descubrimiento", "No se han elegido receptores")
		else:
			tx_selected = tx.get()
			rx_selected = []
			for receiver in rx:
				rx_selected.append(receiver.get())

			connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			json_msg = json.dumps({"rx": rx_selected})
			if len(json_msg) < 255:
				len_length = 0
				if len(json_msg) < 10:
					len_length = 1
				elif len(json_msg) < 100:
					len_length = 2
				else:
					len_length = 2

				msg = "\x11%d%d%s" % (len_length, len(json_msg), json_msg)
				print msg
				connection.connect((tx_selected, 3000))
				connection.send(msg)
				connection.close()
			else:
				print "#ERROR: Message too long"

	def reboot(self, parent, controller):
		"""Reinicia el administrador y vuelve a la página inicial.

		"""
		if self.sock != None:
			self.sock.close()

		for i in self.mutant_buttons:
			i.destroy()
		self.conn_button.destroy()

		self.label_tx.grid(row=0, column=0)
		self.label_rx.grid(row=0, column=1)
		self.discover_button.grid(row=1, column=0, columnspan=2, sticky=NSEW)
		self.return_button.grid(row=2, column=0, sticky=NSEW)
		self.stop_button.grid(row=2, column=1, sticky=NSEW)

		self.grid_rowconfigure(0, weight=1)
		self.grid_rowconfigure(1, weight=1)
		self.grid_rowconfigure(2, weight=1)
		self.grid_columnconfigure(0, weight=2)
		self.grid_columnconfigure(1, weight=2)

		controller.show_frame(StartPage)

	def close_discovery(self, parent, controller):
		"""Cierra el programa.

		"""
		if self.sock != None:
			self.sock.close()
		parent.quit()

	def __init__(self, parent, controller):
		"""Crea la página del administrador.

		"""
		Frame.__init__(self, parent)

		#	Iniciamos las variables propias de la Clase
		self.tx = None
		self.rx = []
		self.sock = None
		self.mutant_buttons = []

		self.label_tx = Label(self, text="Transmisores")
		self.label_rx = Label(self, text="Receptores")

		self.discover_button = ttk.Button(self, text="Descubrir",
										  command=lambda: self.mutant_discovery(parent, controller))

		self.return_button = ttk.Button(self, text="Volver", command=lambda: self.reboot(parent, controller))
		self.stop_button = ttk.Button(self, text="Cerrar", command=lambda: self.close_discovery(parent, controller))

		self.label_tx.grid(row=0, column=0)
		self.label_rx.grid(row=0, column=1)
		self.discover_button.grid(row=1, column=0, columnspan=2, sticky=NSEW)
		self.return_button.grid(row=2, column=0, sticky=NSEW)
		self.stop_button.grid(row=2, column=1, sticky=NSEW)

		self.grid_rowconfigure(0, weight=1)
		self.grid_rowconfigure(1, weight=1)
		self.grid_rowconfigure(2, weight=1)
		self.grid_columnconfigure(0, weight=2)
		self.grid_columnconfigure(1, weight=2)


if __name__ == "__main__":
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
	elif len(sys.argv) == 2:
		if sys.argv[1] == '--help':
			print "Si quiere activar las trazas del programa use los siguientes argumentos:"
			print "--DEBUG=G -> Para activar las trazas de GStreamer"
			sys.exit()
		elif sys.argv[1] == '--DEBUG=G':
			gst.debug_set_active(True)
			gst.debug_set_default_threshold(3)
		else:
			print "#ERROR: Argumento no valido"
			sys.exit()

	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.connect(("gmail.com", 80))
	mutant_ip, port = s.getsockname()

	app = mutantGUI()
	app.title("Mutante de Cerebro")
	app.mainloop()
