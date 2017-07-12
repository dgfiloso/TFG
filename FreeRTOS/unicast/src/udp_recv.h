/**
* @brief Cabecera - Servidor UDP que recibe el audio.
*
* @file udp_recv.h
* @version 3.0
* @author David González Filoso <dgfiloso@b105.upm.es>
* @company B105 - Electronic Systems Lab
*/
#ifndef UDP_RECV_H
#define UDP_RECV_H

#include "semphr.h"
#include "queue.h"

/**
 * @struct recv_data
 * @brief Datos globales del receptor.
 *
 * Esta estructura almacena datos globales para todas las funciones del receptor UDP.
 */
struct recv_data {
  struct udp_pcb* udp_conn;			//!< Socket del servidor
  struct ip_info* local_ip_info;	//!< Dirección IP del módulo
  QueueHandle_t bufferQueue;		//!< Cola para comunicar los datos entre tareas
};

//	Conexión del servidor UDP
struct recv_data* connect_udp(QueueHandle_t bufferQueue_p);

//	Desconexión del servidor UDP
void disconnect_udp(struct recv_data* data_m);

#endif /* UDP_RECV_H */
