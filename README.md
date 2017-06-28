# README #

# Trabajo de Fin de Grado - Diseño e implementación de una red de nodos inalámbricos para comunicaciones multipunto de contenido multimedia.

##	Resumen
+ David González Filoso
+ B105 Electronic Systems Lab
+ Escuela Técnica Superior de Ingenieros de Telecomunicación
+ Universidad Politécnica de Madrid
+ Versión : 2.3
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

##	Cliente de Python
+ Instalar python y python-pip.
+ Instalar gstreamer1.0, gstreamer1.0-* , python-gst-1.0.
+	Instalar python-tk.
+ Descargar los archivos de la carpeta Cliente.
+ Si se desea recibir ayuda a la hora de ejecutar el script se puede usar el flag --help. Con ese flag se pueden ver las posibilidades de flags de depuración que tiene el script.

##	Cliente ESP8266
Se va a hacer uso del firmware NodeMcu. Con este firmware se puede subir scripts de Lua al ESP8266.
+	Primero, hay que obtener el firmware con las librerías que se desean usar, mi recomendación es obtenerlo desde su compilador en la nube.

	https://nodemcu-build.com/

+ Segundo, hay que flashear el firmware en el ESP8266. Yo utilizo esptool.py para ello.

	esptool.py --port <usb-port> write_flash -fm dio 0x00000 <nodemcu-firmware>.bin

+	Tercero, usando la herramienta ESPlorer, nos conectamos al ESP8266 y le subimos los scripts de Lua. Con esta herramienta también contamos con una consola para ver las trazas del programa.

##	Versiones
+	Versión 2.3:

	Se ha mejorado la apariencia de la página web de control haciendo uso de Bootstrap. También se ha creado una interfaz gráfica para el script del cliente. Se ha realizado una implementación del cliente del ESP8266 usando Lua pero han aparecido problemas de memoria al recibir los datos, se llenaba la memoria antes de procesarlos.

+	Versión 2.2:

	He implementado el concepto de "habitación". Un transmisor transmite de manera independiente en una "habitación". Desde el gestor web hay que conectar los receptores a una "habitación" para que puedan recibir el audio.

+	Versión 2.1:

	Se ha añadido un gestor web que corre en el puerto 5000 del servidor. En este gestor se pueden ver los transmisores y receptores conectados, así como la tasa binaria que se está usando.

+ Versión 2.0:

	El servidor se mantiene ejecutándose en una Raspberry Pi o en un ordenador pero ahora pasa a usar la librería Websocket. El cliente se ejecuta en un ordenador y pasa a programarse en Python, se controla mediante la línea de comandos. Puede ser transmisor o receptor.

+	Versión 1.0:

	El servidor se ejecuta en una Raspberry Pi o en un ordenador. Los clientes son solo ordenadores, con el mismo código, que a través de una interfaz por línea de comandos se indica si eres transmisor o receptor.
