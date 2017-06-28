--  GPIO
LED_AMARILLO    = 1     -- GPIO5    - D1
LED_ROJO        = 8     -- GPIO15   - D8
LED_BLANCO      = 7     -- GPIO13   - D7
LED_INTEGRADO   = 0     -- GPIO16   - D0 Led integrado

-- Wifi Credentials
SSID        = "XXXX"      --  SSID de la red WiFi
PASSWORD    = "XXXX"      --  Contraseña de la red WiFi

--  Script principal
local mainScript = "SPIclient.lua"

--  Comportamiento led
local newWifiEvent = 0
local wifiConnected = 0

local function connectionLed(cb_timer)
    if newWifiEvent == 0 then
        wifi.sta.eventMonReg(wifi.STA_FAIL, function()
            cb_timer:unregister()
        end)
        newWifiEvent = 1
        wifi.sta.eventMonStart()
    end
    if wifiConnected == 0 then
        gpio.write(LED_BLANCO, gpio.HIGH)
        gpio.write(LED_AMARILLO, gpio.LOW)
        wifiConnected = 1
    elseif wifiConnected == 1 then
        gpio.write(LED_BLANCO, gpio.LOW)
        gpio.write(LED_AMARILLO, gpio.HIGH)
        wifiConnected = 0
    end
end

local function start_mainScript()
    if file.open(mainScript) == nil then
        print(mainScript.."deleted or renamed")
    else
        print("Running")
        file.close(mainScript)

        --  Ejecutamos script principal
        print("Vamos a ejecutar el script principal...")
        dofile(mainScript)
    end
end

--  GPIO Configuration
print("Configuring GPIO...")
gpio.mode(LED_AMARILLO, gpio.OUTPUT)
gpio.mode(LED_ROJO, gpio.OUTPUT)
gpio.mode(LED_BLANCO, gpio.OUTPUT)
gpio.mode(LED_INTEGRADO, gpio.OUTPUT)

gpio.write(LED_ROJO, gpio.HIGH)
gpio.write(LED_AMARILLO, gpio.LOW)

--  WiFi Connection
print("Connecting to WiFi access point...")
wifi.setmode(wifi.STATION)
wifi.sta.config(SSID, PASSWORD)
-- wifi.sta.connect() not necessary because config() uses auto-connect=true by default
tmr.create():alarm(1000, tmr.ALARM_AUTO, function(cb_timer)
    if wifi.sta.getip() == nil then
        print("Waiting for IP address...")
    else
        cb_timer:unregister()
        print("WiFi connection established, IP address: " .. wifi.sta.getip())
        gpio.write(LED_ROJO, gpio.LOW)

        --  Aviso de leds sobre conexion
        tmr.create():alarm(500, tmr.ALARM_AUTO, connectionLed)
        start_mainScript()
    end
end)
