/*
 * gdbstub-freertos.c
 *
 *  Created on: Sep 29, 2016
 *      Author: vlad
 */

#include "gdbstub.h"
#include "gdbstub-cfg.h"
#include "gdbstub-internal.h"

#include <sys/types.h>

#include <FreeRTOS.h>
#include <task.h>

#include <stdint.h>
#include <stdio.h>

static size_t task_count = 0;
static size_t task_selected = 0;
static struct {
	uint32_t * stack;
	TaskHandle_t handle;
} task_list[GDBSTUB_THREADS_MAX] = {{ 0 }};

/*
 * tskTCB is private, so, unfortunately, we have
 * to redefine it here in order to save some memory
 * by not calling uxTaskGetSystemState()
 *
 * Shouldn't be a big problem since pxTopOfStack
 * is always first.
 */
typedef struct tskTaskControlBlock {
	volatile portSTACK_TYPE * pxTopOfStack;
} tskTCB;

/*
 * Private FreeRTOS stuff shared using portREMOVE_STATIC_QUALIFIER
 */
extern List_t * volatile pxDelayedTaskList;
extern List_t * volatile pxOverflowDelayedTaskList;
extern List_t pxReadyTasksLists[configMAX_PRIORITIES];

#if INCLUDE_vTaskDelete
extern List_t xTasksWaitingTermination;
#endif

#if INCLUDE_vTaskSuspend
extern List_t xSuspendedTaskList;
#endif

extern tskTCB * volatile pxCurrentTCB;

static void gdbstub_send_task(size_t id, char * name) {
	char thread_entry[100] = { 0 };
	const char * thread_template = "<thread id=\"%x\" core=\"0\" name=\"%s\"></thread>";

	snprintf(thread_entry, sizeof(thread_entry), thread_template, id, name);
	gdb_packet_str(thread_entry);
}

static void process_task_list(List_t * list) {
	volatile tskTCB * next_tcb, * first_tcb;

	if (list->uxNumberOfItems > 0) {
		listGET_OWNER_OF_NEXT_ENTRY(first_tcb, list);

		do {
			if (task_count > GDBSTUB_THREADS_MAX) {
				break;
			}

			listGET_OWNER_OF_NEXT_ENTRY(next_tcb, list);

			task_list[task_count].stack = (uint32_t *) next_tcb->pxTopOfStack;
			task_list[task_count].handle = (TaskHandle_t) next_tcb;

			task_count++;
		} while (next_tcb != first_tcb);
	}
}

static void fill_task_array() {
	int32_t queue = configMAX_PRIORITIES;

	task_count = 0;

	do {
		queue--;
		process_task_list(&pxReadyTasksLists[queue]);
	} while (queue > tskIDLE_PRIORITY);

	process_task_list((List_t *) pxDelayedTaskList);
	process_task_list((List_t *) pxOverflowDelayedTaskList);

#if INCLUDE_vTaskDelete
	process_task_list(&xTasksWaitingTermination);
#endif

#if INCLUDE_vTaskSuspend
	process_task_list(&xSuspendedTaskList);
#endif
}

void gdbstub_freertos_task_list() {
	gdb_packet_start();
	gdb_packet_str("l");
	gdb_packet_str("<?xml version=\"1.0\" ?>");
	gdb_packet_str("<threads>");

	/*
	 * It is assumed that the task array doesn't need
	 * to be updated because it already was when the
	 * stop reason was reported.
	 *
	 * Thread ID 0 has a special meaning in the remote
	 * protocol and so is avoided.
	 */

	for (size_t i = 0; i < task_count - 1; i++) {
		gdbstub_send_task(i + 1, (char *) pcTaskGetName(task_list[i].handle));
	}

	gdb_packet_str("</threads>");
	gdb_packet_end();
}

void gdbstub_freertos_task_select(size_t gdb_task_index) {
	task_selected = gdb_task_index - 1;
}

bool gdbstub_freertos_task_selected() {
	if (task_selected > task_count - 1) {
		return true;
	}

	return task_list[task_selected].handle == (TaskHandle_t) pxCurrentTCB;
}

void gdbstub_freertos_regs_read() {
	// task_selected was checked before
	gdb_packet_start();

	uint32_t * task_regs = task_list[task_selected].stack;

	for (size_t i = 3; i <= 18; i++) {
		gdb_packet_hex(bswap32(task_regs[i]), 32);
	}

	// pc
	gdb_packet_hex(bswap32(task_regs[1]), 32);

	// Skip special registers
	gdb_packet_hex(0, 32);
	gdb_packet_hex(0, 32);
	gdb_packet_hex(0, 32);
	gdb_packet_hex(0, 32);

	// ps
	gdb_packet_hex(task_regs[2], 32);

	gdb_packet_end();
}

void gdbstub_freertos_report_thread() {
	fill_task_array();

	size_t task_index = 0;

	for (size_t i = 0; i < task_count - 1; i++) {
		if (task_list[i].handle == (TaskHandle_t) pxCurrentTCB) {
			task_index = i;
			break;
		}
	}

	gdb_packet_str("thread:");
	gdb_packet_hex(task_index + 1, 8);
	gdb_packet_str(";");
}
