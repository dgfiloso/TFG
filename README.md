# README #

# Trabajo de Fin de Grado - Transmisión inalámbrica multipunto de audio/video

* Autor : David González Filoso
* B105 Electronic Systems Lab
* Escuela Técnica Superior de Ingenieros de Telecomunicación
* Universidad Politécnica de Madrid
* Version : 1.0
* Resumen :
	Diseño e implementación de una red de nodos inalámbricos para comunicaciones multipunto de contenido multimedia.

* Estructura :
	El sistema va a estar formado por dos partes:
	+ Servidor node.js implementado en una Raspberry Pi 3 model B.
	+ Cliente que puede ser transmisor o receptor. En esta versión el cliente será un ordenador.

* Requisitos :
	+ Instalar ffmpeg y libav-tools
	+ Instalar pulseaudio

* Características versión 1:
	El servidor se ejecuta en una Raspberry Pi o en un ordenador. Los clientes son solo ordenadores, con el mismo código, que a través de una interfaz por línea de comandos se indica si eres transmisor o receptor.

* Funcionamiento servidor :
	+ Descargar los archivos main.js y package.json de la carpeta servidor
	+ Ejecutar el comando 'npm install' para instalar las librerías
	+ Ejecutar el comando 'npm start' para ejecutar el servidor

* Funcionamiento cliente :
	+ Descargar los archivos pc_client.js y package.json de la carpeta Clientes/PC_Client
	+ Ejecutar el comando 'npm install' para instalar las librerías
	+ Ejecutar el comando 'npm start' para ejecutar el cliente

	# Trabajo de Fin de Grado - Comunicación inalámbrica multipunto de contenido multimedia

	##	Resumen
	* David González Filoso
	* B105 Electronic Systems Lab
	* Escuela Técnica Superior de Ingenieros de Telecomunicación
	* Universidad Politécnica de Madrid
	* Versión : 1.0
	* Descripción :

		Diseño e implementación de una red de nodos inalámbricos para comunicaciones multipunto de contenido multimedia.

	##	Estructura
		El sistema va a estar formado por dos partes:
		+ Servidor node.js implementado en una Raspberry Pi 3 model B.
		+ Cliente que puede ser transmisor o receptor. En esta versión el cliente será un ordenador.

	##	Servidor
		+ Instalar nodejs, nodejs-legacy y npm.
		+ Descargar los archivos de la carpeta Servidor.
		+ Ejecutar el comando 'npm install' para instalar las librerí­as en la carpeta Servidor.
		+ Ejecutar el comando 'npm start' para ejecutar el servidor	en la carpeta Servidor.

	##	Cliente
		+ Instalar nodejs, nodejs-legacy y npm.
		+	Instalar pulseaudio, ffmpeg y libav-tools.
		+ Descargar los archivos de la carpeta Cliente.
		+ Ejecutar el comando 'npm install' para instalar las librerí­as en la carpeta Cliente.
		+ Ejecutar el comando 'npm start' para ejecutar el servidor	en la carpeta Cliente.

	##	Versiones
		+	Versión 1.0:

			El servidor se ejecuta en una Raspberry Pi o en un ordenador. Los clientes son solo ordenadores, con el mismo código, que a través de una interfaz por línea de comandos se indica si eres transmisor o receptor.
