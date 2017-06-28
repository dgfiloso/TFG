var ip = location.host;
console.log(ip);
var socket = io.connect('http://'+ip+'', {'forceNew' : true});

socket.on('refreshTable', function(){

	//	Actualizamos la tabla del navegador
	$("#tabla").load("/" + " #tabla");
	console.log("Se ha actualizado la tabla");
});

socket.on('refreshBitRate', function(){
	//	Actualizamos la tabla del navegador
	$("#bitRate").load("/" + " #bitRate");
	console.log("Se ha actualizado la tasa de bits");
});
