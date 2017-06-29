/**
* @brief Cabecera - Lógica de control con el servidor Cerebro y gestión del audio recibido.
*
* @file mutant.h
* @version 2.4
* @author David González Filoso <dgfiloso@b105.upm.es>
* @company B105 - Electronic Systems Lab
**/
#ifndef MUTANT_H
#define MUTANT_H

#include "fsm.h"

//  Crea una máquina de estados
fsm_t* fsm_mutant_new(void);

//  Devuelve la cantidad de datos que se han recibido
size_t rcv_socket_size(void);

//  Conecta el cliente al servidor
int mutant_connect(const char *server_ip, const int server_port);

#endif
