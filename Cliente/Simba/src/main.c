/**
* @brief Código - Cliente del servidor Cerebro. Recibe audio y lo envía por SPI para reproducirlo.
*
* Programa para el módulo ESP8266 utilizando el sistema operativo de tiempo real Simba.
* Se conecta al sistema Cerebro a través de Websocket siempre como receptor. Una vez conectado
* espera a que se le comunique con un transmisor para recibir el audio que este envía y
* reproducirlo mandándolo por SPI.
*
* @file main.c
* @version 2.5
* @author David González Filoso <dgfiloso@b105.upm.es>
* @company B105 - Electronic Systems Lab
*/

#include "simba.h"
#include "fsm.h"
#include "wifi_conn.h"
#include "mutant.h"
#include "mp3_decoder.h"

#define WIFI_SSID   "XXXX"              //  WiFi ssid
#define WIFI_PASSW  "XXXX"              //  WiFi password
#define SERVER_IP   "XX.XX.XX.XX"       //  Server IP
#define SERVER_PORT 3000

/**
 *  @brief  Función principal del programa.
 *
 *  Inicia el sistema conectándolo por WiFi e iniciando una máquina de estados.
 *  Esta máquina de estados realiza toda la lógica para gestionar la conexión por
 *  Websocket con el servidor, así como la recepción del audio.
 *
 *  @param void
 *  @return int Entero que indica si el programa ha terminado correctamente, 0 en ese caso.
 */
int main(void)
{
  fsm_t* mutant_m;

  sys_start();    //  Start default configuration

  std_printf(sys_get_info());

  wifi_connect(WIFI_SSID, WIFI_PASSW);

  mutant_m = fsm_mutant_new();

  if (mutant_connect(SERVER_IP, SERVER_PORT) == 0)
  {
    std_printf(OSTR("Mutant connected!\n"));
  }

  // configureMp3();

  while(1)
  {
    fsm_fire(mutant_m);
  }

  return 0;
}
