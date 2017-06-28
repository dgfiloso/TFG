-- Las variables locales son más raidas para acceder https://codea.io/talk/discussion/2089/constants-in-lua
--	CONSTANTES
--	Websocket constants
local IP 			= "X.X.X.X"		-- IP del servidor
local PORT 		= 3000
local name 		= "NodeMCU"
local type 		= "R"

--	SPI constants
local ID				= 0
local MODE			= spi.MASTER
local CPOL			= spi.CPOL_LOW
local CPHA			= spi.CPHA_LOW
local DATABITS	= 32
local CLOCK_DIV	= 0
local DREQ			= 2		-- GPIO4
local XCS 			= 12 	-- GPIO10
local XDCS			= 4	-- GPIO2
local RST				= 5		-- GPIO14	Activo a nivel bajo

--	VS10xx SCI Registers
local SCI_MODE 				= 0x00
local SCI_STATUS 			= 0x01
local SCI_BASS 				= 0x02
local SCI_CLOCKF 			= 0x03
local SCI_DECODE_TIME = 0x04
local SCI_AUDATA 			= 0x05
local SCI_WRAM 				= 0x06
local SCI_WRAMADDR 		= 0x07
local SCI_HDAT0 			= 0x08
local SCI_HDAT1 			= 0x09
local SCI_AIADDR 			= 0x0A
local SCI_VOL 				= 0x0B
local SCI_AICTRL0 		= 0x0C
local SCI_AICTRL1 		= 0x0D
local SCI_AICTRL2 		= 0x0E
local SCI_AICTRL3 		= 0x0F


-- Variables
local conn

--	********************************************************************
--	GPIO functions
local function init_GPIO()
	gpio.mode(DREQ, gpio.INPUT)
	gpio.mode(XDCS, gpio.OUTPUT)
	gpio.mode(XCS, gpio.OUTPUT)
	gpio.mode(RST, gpio.OUTPUT)

	gpio.write(RST, gpio.LOW)
	gpio.write(XDCS, gpio.HIGH)
	gpio.write(XCS, gpio.HIGH)
end

--	*********************************************************************
--	VS10xx functions
local function Mp3WriteRegister(addressbyte, highbyte,lowbyte)
	command = {};
	command[0] = 0x02;
	command[1] = addressbyte;
	command[2] = highbyte;
	command[3] = lowbyte;

	while(gpio.read(DREQ) == 0) do
	end

	gpio.write(XCS,gpio.LOW)
	spi.send(ID, command)
	gpio.write(XCS,gpio.HIGH)

	while(gpio.read(DREQ) == 0) do
	end
end

--	*********************************************************************
--	SPI functions

local function init_SPI()
	gpio.write(RST, gpio.LOW)
	tmr.delay(1000000)
	gpio.write(RST, gpio.HIGH)
	tmr.delay(1000000)
	spi.setup(ID, MODE, CPOL, CPHA, DATABITS, CLOCK_DIV)

	Mp3WriteRegister(SCI_MODE, 0x08, 0x0C)
	Mp3WriteRegister(SCI_VOL, 0x00, 0x00)
	Mp3WriteRegister(SCI_CLOCKF, 0x60, 0x00)
	print("Configurado el decodificador")

end

-- **********************************************************************
--	Websocket functions

local function cb_connection(conn)
	print('got ws connection')
	print('Memoria inicial: '..node.heap())
	ok, json = pcall(cjson.encode, {event="clientInfo", name=name, type=type})
	if ok then
		conn:send(json)
		print("send clientInfo correctly!")
	else
		print("failed to encode!")
	end
end

local function cb_receive(conn, msg, opcode)
	if opcode == 1 then
		t = cjson.decode(msg)
		if t.event == "ACK" then
			print(t.data)
		else
			print('got message: ', msg, opcode)
		end
	elseif opcode == 2 then

		print("Memoria: "..node.heap())
		--print ("Tamaño del paquete"..msg.len)

		print("DREQ = " ..gpio.read(DREQ))
		while gpio.read(DREQ) == 0 do
		end

		print ("Ponemos XDCS a nivel bajo")
		gpio.write(XDCS, gpio.LOW)
		print ("Pasamos a enviar los bytes")
		local bytes = spi.send(ID, msg)
		gpio.write(XDCS, gpio.HIGH)
		-- while bytes < 32 do
		-- 	print ("Enviando...")
		-- end
		print("Enviados "..bytes.." bytes")

		while gpio.read(DREQ) == 0 do
		end
	end
end

local function cb_close(conn, status)
	print('connection closed ', status)
	ws = nil
end

local function init_websocketClient()
	conn = websocket.createClient()
	print("Creado cliente de websocket")
	conn:close()
	--conn:config({headers={['Sec-Websocket-Protocol']='echo'}})
	local url ='ws://'..IP..':'..PORT 				-- Los dos puntos .. son para concatenar string
	conn:connect(url)

	conn:on('connection', cb_connection)
	conn:on('receive', cb_receive)
	conn:on('close', cb_close)
end

--	************************************************************
--	Main

print("Comienza nuestro script")

init_GPIO()
print("GPIO Configurado")
init_SPI()
print("SPI Configurado")
--	Inicializamos el cliente de websocket
init_websocketClient()
