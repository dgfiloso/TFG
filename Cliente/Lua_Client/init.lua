
function startup()
    if file.open("init.lua") == nil then
        print("init.lua deleted or renamed")
    else
        print("Running")
        file.close("init.lua")

  		--	Configuramos el Garbage Collector
        node.egc.setmode(node.egc.ALWAYS)
        print("Garbage Collector configured")

        --	Ejecutamos los scripts
        print("Vamos a ejecutar el script de conexion...")
        dofile("wifi_conn.lua")
    end
end

print("You have 3 seconds to abort")
print("Waiting...")
tmr.create():alarm(3000, tmr.ALARM_SINGLE, startup)
