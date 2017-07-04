/** xtensa_ops.h
 *
 * Special macros/etc which deal with Xtensa-specific architecture/CPU
 * considerations.
 *
 * Part of esp-open-rtos
 * Copyright (C) 2015 Superhouse Automation Pty Ltd
 * BSD Licensed as described in the file LICENSE
 */

#ifndef _XTENSA_OPS_H
#define _XTENSA_OPS_H

/* Read stack pointer to variable.
 *
 * Note that the compiler will push a stack frame (minimum 16 bytes)
 * in the prelude of a C function that calls any other functions.
 */
#define SP(var) __asm volatile ("mov %0, a1" : "=r" (var))

/* Read the function return address to a variable.
 *
 * Depends on the containing function being simple enough that a0 is
 * being used as a working register.
 */
#define RETADDR(var) __asm volatile ("mov %0, a0" : "=r" (var))

// GCC macros for reading, writing, and exchanging Xtensa processor special
// registers:

#define RSR(var, reg) __asm volatile ("rsr %0, " #reg : "=r" (var));
#define WSR(var, reg) __asm volatile ("wsr %0, " #reg : : "r" (var));
#define XSR(var, reg) __asm volatile ("xsr %0, " #reg : "+r" (var));

// GCC macros for performing associated "*sync" opcodes

#define ISYNC() __asm volatile ( "isync" )
#define RSYNC() __asm volatile ( "rsync" )
#define ESYNC() __asm volatile ( "esync" )
#define DSYNC() __asm volatile ( "dsync" )

#endif /* _XTENSA_OPS_H */
