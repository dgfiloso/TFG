/**
* @brief Sobreescritura del fichero FreeRTOS.h.
*
* Se utiliza este fichero para indicar los valores que el usuario quiere configurar en FreeRTOS.h
* y así se deja ese fichero con los valores por defecto.
*
* @file FreeRTOSConfig.h
* @version 3.0
* @author David González Filoso <dgfiloso@b105.upm.es>
* @company B105 - Electronic Systems Lab
*/

/* We sleep a lot, so cooperative multitasking is fine. */
#define configUSE_PREEMPTION 0

/* Blink doesn't really need a lot of stack space! */
#define configMINIMAL_STACK_SIZE 128

#define configTOTAL_HEAP_SIZE		( ( size_t ) ( 32 * 1024 ) )

/* Use the defaults for everything else */
#include_next<FreeRTOSConfig.h>
