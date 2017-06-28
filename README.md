# README #

# Trabajo de Fin de Grado - Diseño e implementación de una red de nodos inalámbricos para comunicaciones multipunto de contenido multimedia.

##	Resumen
+ David González Filoso
+ B105 Electronic Systems Lab
+ Escuela Técnica Superior de Ingenieros de Telecomunicación
+ Universidad Politécnica de Madrid
+ Versión : 2.0
+ Descripción :

	Diseño e implementación de una red de nodos inalámbricos para comunicaciones multipunto de contenido multimedia.

##	Estructura
El sistema va a estar formado por dos partes:
+ Servidor node.js implementado en una Raspberry Pi 3 model B.
+ Cliente que puede ser transmisor o receptor. En esta versión el cliente será un ordenador controlado por línea de comandos.

##	Servidor
+ Instalar nodejs, nodejs-legacy y npm.
+ Descargar los archivos de la carpeta Servidor.
+ Ejecutar el comando 'npm install' para instalar las librerí­as en la carpeta Servidor.
+ Ejecutar el comando 'npm start' para ejecutar el servidor	en la carpeta Servidor.

##	Cliente
+ Instalar python y python-pip.
+ Instalar gstreamer1.0, gstreamer1.0-* , python-gst-1.0
+ Descargar los archivos de la carpeta Cliente.

##	Versiones
+	Versión 2.1:

	Se ha añadido un gestor web que corre en el puerto 5000 del servidor. En este gestor se pueden ver los transmisores y receptores conectados, así como la tasa binaria que se está usando.
	
+ Versión 2.0:

	El servidor se mantiene ejecutándose en una Raspberry Pi o en un ordenador pero ahora pasa a usar la librería Websocket. El cliente se ejecuta en un ordenador y pasa a programarse en Python, se controla mediante la línea de comandos. Puede ser transmisor o receptor.

+	Versión 1.0:

	El servidor se ejecuta en una Raspberry Pi o en un ordenador. Los clientes son solo ordenadores, con el mismo código, que a través de una interfaz por línea de comandos se indica si eres transmisor o receptor.
