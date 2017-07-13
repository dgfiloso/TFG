#!/usr/bin/python
# -*- coding: utf-8 -*-
"""*************************************************************
*   @file       unicast_tx.py
*   @version    3.0
*   @author     David González Filoso <dgfiloso@b105.upm.es>
*   @company    B105 Electronic Systems Lab
*   @description Transmisor unicast del sistema Cerebro
*************************************************************"""
import threading  # Librería para usar distintas hebras
import subprocess  # Librería para usar procesos del sistema
import sys  # Librería para usar el sistema
import socket  # Librería para usar sockets
import struct  # Librería para usar estructuras como en C
import string
import binascii

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

tx_pipeline 	= None  			# Pipeline de transmisión
udp_conn = None  #  Socket UDP
udp_addr = "10.7.22.13"  # Dirección para comunicación UDP
udp_port = 4000
f = open("audio.mp3", 'w')

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
	# hex_str = binascii.b2a_hex(tx_data)
	# print hex_str
	f.write(tx_data)
	udp_conn.sendto(tx_data, (udp_addr, udp_port))
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

def send_audio():
	"""Tomamos el audio del sistema y lo transmitimos mediante sockets.

	Esta función se puede dividir en cinco partes claras:

	1. 	Creamos un socket UDP

	2.	Buscamos el número de nuestra tarjeta de sonido y cambiamos la entrada
	    de audio a 'Monitor of' para crear un enlace entre los altavoces y
	    el micrófono.

	3.	Creamos un pipeline de transmisión que lee el micrófono y envía sus
	    datos mediante sockets.

	Elementos del pipeline de transmisión:

	-	pulsesrc		-- Lee los datos del micrófono
	-	audioconvert	-- Elemento usado para la conversión
	-	lamemp3enc		-- Convierte los datos del micrófono a MP3
	-	appsink			-- Elemento utilizado para obtener los datos y transmitirlos

	"""
	#   ****** 1. Creamos el socket UDP
	global udp_conn
	udp_conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	#	******* 2. Buscamos el número de nuestra tarjeta de sonido
	p = subprocess.Popen(['pacmd', 'list-cards'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	g = subprocess.Popen(['grep', 'device.bus_path'], stdin=p.stdout, stdout=subprocess.PIPE,
	                     stderr=subprocess.STDOUT)
	soundCard = g.stdout.read().split('"')[1]
	# print "Numero del bus de la tarjeta de sonido: "+soundCard
	soundCard = soundCard.replace(":", "_")

	# print "Vamos a ejecutar: "+'pacmd set-default-source alsa_output.'+soundCard+'.analog-stereo.monitor'
	subprocess.call(['pacmd', 'set-default-source', 'alsa_output.' + soundCard + '.analog-stereo.monitor'])

	#	******* 3. Creamos un pipeline de transmisión y comenzamos a transmitir
	global tx_pipeline

	#	Implementación con GStreamer
	tx_pipeline = gst.Pipeline()

	audio_src = gst.ElementFactory.make("pulsesrc", "audio_src")
	convert = gst.ElementFactory.make("audioconvert", "convert")
	encoder = gst.ElementFactory.make("lamemp3enc", "encoder")
	audio_sink = gst.ElementFactory.make("appsink", "audio_sink")

	encoder.set_property('target', 'bitrate')
	encoder.set_property('bitrate', 32)
	audio_sink.set_property('emit-signals', True)  # Permite emitir las señales 'new-sample' y 'new-preroll'
	audio_sink.set_property('sync', False)  # Hace la decodificacion lo mas rapida posible
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

	print "SENDING DATA..."

	GObject.MainLoop().run()

if __name__ == "__main__":
    """Función principal que lanza las distintas funciones.

    Lanza el objeto de GStreamer y las tareas de comunicación. Además en función de los
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

    try:
        send_audio()

    except KeyboardInterrupt:
		udp_conn.close()
		f.close()
		sys.exit()
