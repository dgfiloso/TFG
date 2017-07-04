# README #

# Trabajo de Fin de Grado - Diseño e implementación de una red de nodos inalámbricos para comunicaciones multipunto de contenido multimedia.

##	Resumen
+ David González Filoso
+ B105 Electronic Systems Lab
+ Escuela Técnica Superior de Ingenieros de Telecomunicación
+ Universidad Politécnica de Madrid
+ Versión : 3.0
+ Descripción :

	Este proyecto busca la implementación de una red de nodos basados en el módulo wifi ESP8266 que pueda comunicar contenido multimedia entre ellos y ordenadores. De esta manera, se podrá escuchar la música de un PC en unos altavoces que no tengan conexión a internet, conectándoles nuestro dispositivo.

##	Estructura
El sistema sólo estará formado por clientes. Estos clientes podrán ser transmisores o receptores y se conectarán a través de un administrador que se comunica con ellos usando un grupo UDP multicast.

##	Cliente de Python
+ Instalar python y python-pip.
+ Instalar gstreamer1.0, gstreamer1.0-* , python-gst-1.0.
+	Instalar python-tk.
+ Descargar los archivos de la carpeta Python.
+ Si se desea recibir ayuda a la hora de ejecutar el script se puede usar el flag --help. Con ese flag se pueden ver las posibilidades de flags de depuración que tiene el script.

##	Cliente ESP8266
Se utiliza el sistema operativo FreeRTOS, utilizando el firmware esp-open-rtos (https://github.com/SuperHouse/esp-open-rtos). Todas las instrucciones para utilizarlo se encuentran en su repositorio. Este cliente no se ha conseguido que reciba datos por un grupo multicast, por lo que he realizado una prueba de funcionamiento utilizando una conexión UDP normal. Para esta prueba, en vez de utilizar el script p2p_client.py como cliente, se tiene que utilizar el script unicast_tx.py como transmisor.

##	Versiones
+ Versión 3.0:

	El sistema se ha descentralizado quitando el servidor Websocket. Ahora los cliente tienen un servidor TCP al que hay que conectarse para controlarlos. Además toda la parte de comunicación del audio se realiza usando un grupo UDP multicast. Para gestionar las conexiones, un administrador que se lanza desde el script p2p_client.py utiliza un grupo multicast para descubrir a los clientes y conectarlos entre ellos.

	En esta versión el ESP8266 no se conecta todavía al sistema global, por lo que he hecho una prueba de funcionamiento utilizando una conexión UDP normal.

+	Versión 2.5:

	En esta versión se utiliza UDP multicast para realizar la comunicación del audio. De esta manera se reduce el consumo de ancho de banda. Cada transmisor comunica su contenido en un grupo multicast distinto, y los receptores se unen a él cuando se lo indica el servidor.

+ Versión 2.4:

	El cliente del ESP8266 se ha pasado a implementar con el sistema operativo Simba. Debido a problemas con el driver del SPI, solo se ha conseguido que cuando reciba los datos, los descarte. Además se ha añadido una opción en la página web para eliminar del sistema clientes.

	Se ha añadido documentación con Doxygen para el cliente del ESP8266 con Simba. Se puede consultar en la carpeta Cliente/Simba_Client/html.

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
