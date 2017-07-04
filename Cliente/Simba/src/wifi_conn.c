/**
* @brief Código - Conexión con una red WiFi.
*
* Conecta el módulo a la red WiFi deseada. Además mediante unos LEDs indica
* al usuario si se ha conectado o no.
*
* @file wifi_conn.c
* @version 2.5
* @author David González Filoso <dgfiloso@b105.upm.es>
* @company B105 - Electronic Systems Lab
*/

#include "simba.h"
#include "wifi_conn.h"

/*  Private functions prototypes ---------------------------------*/

//  Activa los indicadores de conexión a red wifi
static void wifi_connected_led(void);

//  Desactiva los indicadores de conexión a red wifi
static void wifi_disconnected_led(void);

/*  Public functions ------------------------------------------*/

/**
 *  @brief  Conecta con una red WiFi
 *
 *  Inicializa en driver de conexión con una red wifi. Inicia el módulo en
 *  modo estación.
 *
 *  @param  ssid_p  String con el SSID de la red WiFi
 *  @param  passw_p String con la contraseña de la red WiFi
 *  @return int Entero que indica si se ha conectado correctamente (0) o algo ha fallado (-1)
 */
int wifi_connect(const char* ssid_p, const char* passw_p)
{
  wifi_disconnected_led();

  esp_wifi_set_op_mode(esp_wifi_op_mode_station_t);   //  Configuramos el módulo como estación Wifi
  esp_wifi_station_set_reconnect_policy(1);           //  Permitimos (True) la reconexión del wifi
  std_printf(OSTR("Connect to %s\n"),ssid_p);

  //  Conectamos el módulo a la red Wifi que le pasamos como parámetro
  if (esp_wifi_station_init(ssid_p, passw_p, NULL) != 0)
  {
    std_printf(OSTR("Failed to configure the Station.\r\n"));
  }

  //  Esperamos a que se conecte a la red
  while(esp_wifi_station_get_status()==esp_wifi_station_status_connecting_t)
  {
    std_printf(OSTR("Connecting...\n"));
    time_busy_wait_us(250000);
  }

  //  Confirmamos que el módulo se ha conectado a la red
  if(esp_wifi_station_get_status()==esp_wifi_station_status_got_ip_t)
  {
    std_printf(OSTR("Connected succesfuly!\n"));
    esp_wifi_print(sys_get_stdout());
    wifi_connected_led();
  }
  else
  {
    std_printf(OSTR("Connection failed!\n"));
    esp_wifi_print(sys_get_stdout());
  }

  return 0;
}

/*  Private functions ----------------------------------------*/

/**
 *  @brief  Enciende un led amarillo y apaga uno rojo al conectarse a la red.
 *
 *  @param  void
 *  @return void
 */
static void wifi_connected_led(void)
{
  struct pin_driver_t red_led;
  struct pin_driver_t yellow_led;

  /* Initialize pin */
  pin_init(&red_led, &pin_d8_dev, PIN_OUTPUT);
  pin_init(&yellow_led, &pin_d1_dev, PIN_OUTPUT);
  pin_write(&red_led, 0);
  pin_write(&yellow_led, 1);
}

/**
 *  @brief  Enciende un led rojo y apaga uno amarillo cuando el módulo está
 *  desconectado de la red.
 *
 *  @param  void
 *  @return void
 */
static void wifi_disconnected_led(void)
{
  struct pin_driver_t red_led;
  struct pin_driver_t yellow_led;

  /* Initialize pin */
  pin_init(&red_led, &pin_d8_dev, PIN_OUTPUT);
  pin_init(&yellow_led, &pin_d1_dev, PIN_OUTPUT);
  pin_write(&red_led, 1);
  pin_write(&yellow_led, 0);
}
