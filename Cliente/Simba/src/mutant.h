/**
* @brief Cabecera - Lógica de control con el servidor Cerebro y gestión del audio recibido.
*
* @file mutant.h
* @version 2.5
* @author David González Filoso <dgfiloso@b105.upm.es>
* @company B105 - Electronic Systems Lab
**/
#ifndef MUTANT_H
#define MUTANT_H

#include "fsm.h"

//  Crea una nueva máquina de estados
fsm_t* fsm_mutant_new(void);

//  Conecta un cliente al servidor Cerebro
int mutant_connect(const char *server_ip, const int server_port);

#endif
