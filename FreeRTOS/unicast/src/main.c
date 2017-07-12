/**
* @brief Código - Cliente del sistema Cerebro. Recibe audio y lo envía para reproducirlo.
*
* Programa para el módulo ESP8266 utilizando el sistema operativo de tiempo real FreeRTOS.
* Mediante el uso de un servidor UDP recibe audio y lo envía a otro módulo para que lo reproduzca.
*
* @file main.c
* @version 3.0
* @author David González Filoso <dgfiloso@b105.upm.es>
* @company B105 - Electronic Systems Lab
*/

#include "espressif/esp_common.h"
#include "esp/uart.h"
#include "esp/gpio.h"
#include "esp8266.h"
#include <softuart/softuart.h>

#include <stdlib.h>
#include "FreeRTOS.h"
#include "task.h"
#include "semphr.h"

#include "lwip/err.h"
#include "lwip/sockets.h"
#include "lwip/sys.h"
#include "lwip/netdb.h"
#include "lwip/dns.h"
#include "lwip/udp.h"

#include "udp_recv.h"

#define WIFI_SSID   "XXXX"    //!<  Nombre de la red wifi
#define WIFI_PASS   "XXXX"    //!<  Contraseña de la red wifi

#define RX_PIN 5              //!<  Pin de recepción del puerto UART software
#define TX_PIN 4              //!<  Pin de transmisión del puerto UART software

/**
 * @struct communication_data
 * @brief Contiene estructuras o variables comunes a las tareas que utilizan para comunicarse entre ellas.
 */
struct communication_data {
  QueueHandle_t bufferQueue_p;		//!< Cola para comunicar audio entre receptor y reproductor
};

/*  Private functions prototypes ***************************************/
static void recv_task(void *pvParameters);
static void decoder_task(void *pvParameters);
static void wifi_task(void *pvParameters);

/*  Global variables **************************************************/
static int wifi_alive = 0;    //!<  Indica si la conexión wifi se encuentra activa (1)

/*  Private functions *************************************************/

/**
 *  @brief  Tarea que se encarga de recibir el audio.
 *
 *  Mediante un servidor UDP, recibe el audio y lo manda a la tarea de reproducción
 *  usando una cola.
 *
 *  @param pvParameters	Parámetro que se le pasa al crear la tarea
 *  @return void
 */
static void recv_task(void *pvParameters)
{
	struct communication_data* comm_data = (struct communication_data*)pvParameters;
	struct recv_data* data_recv;

//	while(wifi_alive == 0 && mp3_ready == 0)
	while(wifi_alive == 0)
	{
		vTaskDelay(1000 / portTICK_PERIOD_MS);
	}

	data_recv = connect_udp(comm_data->bufferQueue_p);

	while(1)
	{
		vTaskDelay(10 / portTICK_PERIOD_MS);
	}

	disconnect_udp(data_recv);
}

/**
 *  @brief  Tarea que se encarga de reproducir el audio.
 *
 *  Recibe el audio a través de una cola y lo envía a otro módulo para que
 *  lo descodifique y lo reproduzca.
 *
 *  @param pvParameters	Parámetro que se le pasa al crear la tarea
 *  @return void
 */
static void decoder_task(void *pvParameters)
{
	struct communication_data* comm_data = (struct communication_data*)pvParameters;
	struct pbuf* p = (struct pbuf*)malloc(sizeof(struct pbuf));
//	struct i2s_data* data_i2s;
	int i;

	while(wifi_alive == 0)
	{
	vTaskDelay(1000 / portTICK_PERIOD_MS);
	}

	while (!softuart_open(0, 115200, RX_PIN, TX_PIN))
	{
		printf("#UART: Cannot open\n");
		vTaskDelay(1000 / portTICK_PERIOD_MS);
	}
	printf("#UART: Opened!\n");

	while (1)
	{
		if( xQueueReceive( (comm_data->bufferQueue_p), p, 0 ) == pdPASS )
		{
			for (i = 0; i < (p->len); i++)
			{
				if (!softuart_put(0, *((char*)((p->payload)+i))))
					printf("#UART: Cannot send %d\n", (p->len));
			}

			printf("#PLAYER: %d bytes played!\n", p->len);
		}

		vTaskDelay(10 / portTICK_PERIOD_MS);
	}
}

/**
 *  @brief  Tarea que se encarga de conectarse a la red wifi.
 *
 *  @param pvParameters	Parámetro que se le pasa al crear la tarea
 *  @return void
 */
static void wifi_task(void *pvParameters)
{
  uint8_t status = 0;
  uint8_t retries = 30;
  const int yellow_led = 12;
  struct sdk_station_config config = {
    .ssid = WIFI_SSID,
    .password = WIFI_PASS, };

  gpio_enable(yellow_led, GPIO_OUTPUT);
  gpio_write(yellow_led, 0);

  printf("#WIFI: %s: Connecting to WiFi\n\r", __func__);
  sdk_wifi_set_opmode (STATION_MODE);
  sdk_wifi_station_set_config(&config);

  while (1) {
      wifi_alive = 0;

      while ((status != STATION_GOT_IP) && (retries)) {
          status = sdk_wifi_station_get_connect_status();
          printf("#WIFI: %s: status = %d\n\r", __func__, status);
          if (status == STATION_WRONG_PASSWORD) {
              printf("#WIFI: Wrong password\n\r");
              break;
          } else if (status == STATION_NO_AP_FOUND) {
              printf("#WIFI:  AP not found\n\r");
              break;
          } else if (status == STATION_CONNECT_FAIL) {
              printf("#WIFI: Connection failed\r\n");
              break;
          }
          vTaskDelay(1000 / portTICK_PERIOD_MS);
          --retries;
      }

      while ((status = sdk_wifi_station_get_connect_status())
              == STATION_GOT_IP) {
          if (wifi_alive == 0) {
              printf("#WIFI: Connected\n\r");
              gpio_write(yellow_led, 1);
              wifi_alive = 1;
          }
          vTaskDelay(500 / portTICK_PERIOD_MS);
      }

      wifi_alive = 0;
      printf("#WIFI: Disconnected\n\r");
      gpio_write(yellow_led, 0);
      vTaskDelay(1000 / portTICK_PERIOD_MS);
  }
}

/*  Main function ***************************************************/

/**
 *  @brief  Función principal del programa
 *
 *  Crea las tareas, las colas y los semáforos.
 *
 *  @param void
 *  @return void
 */
void user_init(void)
{
  TaskHandle_t *recvTask_h = (TaskHandle_t*)malloc(sizeof(TaskHandle_t));
  TaskHandle_t *decoderTask_h = (TaskHandle_t*)malloc(sizeof(TaskHandle_t));
  TaskHandle_t *wifiTask_h = (TaskHandle_t*)malloc(sizeof(TaskHandle_t));
  struct communication_data* data_m = (struct communication_data*)malloc(sizeof(struct communication_data));
  data_m->bufferQueue_p = xQueueCreate(1000, sizeof(struct pbuf));


  uart_set_baud(0, 115200);
  printf("SDK version:%s\n", sdk_system_get_sdk_version());

  xTaskCreate(&recv_task, "recvTask", 256, data_m, 3, recvTask_h);
  xTaskCreate(&decoder_task, "decoderTask", 256, data_m, 2, decoderTask_h);
  xTaskCreate(&wifi_task, "wifiTask", 256, NULL, 1, wifiTask_h);
}
