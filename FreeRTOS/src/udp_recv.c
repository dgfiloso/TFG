/**
* @brief Código - Servidor UDP que recibe el audio.
*
* Creamos un servidor UDP que espera a recibir conexiones y datos para enviarlos por una cola
* a la tarea de reproducción.
*
* @file udp_recv.c
* @version 3.0
* @author David González Filoso <dgfiloso@b105.upm.es>
* @company B105 - Electronic Systems Lab
*/
#include <string.h>

#include "espressif/esp_common.h"
#include "esp/uart.h"
#include "FreeRTOS.h"

#include "lwip/api.h"
#include "lwip/err.h"
#include "lwip/sockets.h"
#include "lwip/sys.h"
#include "lwip/netdb.h"
#include "lwip/dns.h"
#include "lwip/inet.h"
#include "lwip/ip_addr.h"
#include "lwip/udp.h"

#include "udp_recv.h"


/*  Private functions prototypes ************************************/
static void udp_rcv_callback(void * arg, struct udp_pcb * upcb, struct pbuf * p, struct ip_addr * addr, u16_t port);

/*  Public functions  ************************************************/

/**
 *  @brief  Creación del servidor UDP escuchando en el puerto 4000.
 *
 *  Crea el servidor y configura los callbacks para las funciones.
 *
 *  @param readyMutex_p Mutex que usaremos para bloquear mientras unos datos se están procesando
 *  @param bufferQueue_p Cola que usaremos para comunicar los datos de audio
 *  @return struct recv_data* Devolvemos una estructura con todos los datos que necesitarán otras funciones
 */
struct recv_data* connect_udp(SemaphoreHandle_t readyMutex_p, QueueHandle_t bufferQueue_p)
{
  err_t err;
  u16_t port = 4000;
  struct recv_data* data_m = (struct recv_data*)malloc(sizeof(struct recv_data));

  data_m->local_ip_info = (struct ip_info*)malloc(sizeof(struct ip_info));
  data_m->udp_conn = udp_new();
  data_m->readyMutex = readyMutex_p;
  data_m->bufferQueue = bufferQueue_p;

  while (1)
  {
    //  Obtenemos nuestra dirección ip local
    if (!sdk_wifi_get_ip_info(0, data_m->local_ip_info))
    {
      printf("#PLAYER: %s : Could not get local ip! (%s)\n", __FUNCTION__, lwip_strerr(err));
      vTaskDelay(100 / portTICK_PERIOD_MS);
      continue;
    }

    // printf("#PLAYER: Local ip -> %s\n", ipaddr_ntoa(&(local_ip_info->ip)));

    //  Creamos un servidor UDP en ip_local:4000
    err =  udp_bind(data_m->udp_conn, &(data_m->local_ip_info->ip), port);
    if (err != ERR_OK)
    {
      printf("#PLAYER: %s : Cannot bind to %s:%d (%s)\n", __FUNCTION__, ipaddr_ntoa(&(data_m->local_ip_info->ip)), port, lwip_strerr(err));
      vTaskDelay(100 / portTICK_PERIOD_MS);
      continue;
    }

    //  Configuramos un callback para la recepción de datos
    udp_recv(data_m->udp_conn, udp_rcv_callback, data_m);

    printf("#UDP: Server listening\n");
    return data_m;
  }
}

/**
 *  @brief  Desconectamos el servidor UDP.
 *
 *  @param data_m Datos globales que debemos liberar y cerrar
 *  @return void
 */
void disconnect_udp(struct recv_data* data_m)
{
  udp_remove(data_m->udp_conn);
  printf("#UDP: Server disconnected\n");
  free(data_m->local_ip_info);
  vSemaphoreDelete(data_m->readyMutex);
  vQueueDelete(data_m->bufferQueue);
  free(data_m);
}

/*  Private functions **************************************************/

/**
 *  @brief  Función que se ejecuta al recibir datos.
 *
 *  Tomamos los datos y los enviamos por la cola a la tarea de reproducción. Antes de enviarlos
 *  necesitamos tomar un mutex, el cual puede estar cogido por la tarea de reproducción.
 *
 *  @param arg Puntero a una estructura que el usuario puede utilizar
 *  @param upcb Socket UDP
 *  @param p Memoria con los datos recibidos
 *  @param addr Dirección de la que proviene los datos
 *  @param port Puerto del que provienen los datos
 *  @return void
 */
static void udp_rcv_callback(void * arg, struct udp_pcb * upcb, struct pbuf * p, struct ip_addr * addr, u16_t port)
{
  struct recv_data* data_m = (struct recv_data*)arg;

  if( xSemaphoreTake( (data_m->readyMutex), 0 ) == pdTRUE )
  {
    if( xQueueSendToBack( (data_m->bufferQueue), p, 0 ) != pdPASS )
    {
      printf("#UDP: Cannot send data to the player\n");
    }
    xSemaphoreGive( (data_m->readyMutex) );
  }

  pbuf_free(p);
}
