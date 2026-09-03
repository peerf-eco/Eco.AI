/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   atomic.h
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает атомарные операции
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __ECO_ATOMIC_H__
#define __ECO_ATOMIC_H__

#ifdef ATOMIC_UTILITY

/* Определение прототипов функций */
int8_t atomicincrement_int8_t(/* in */ int8_t val);
int16_t atomicincrement_int16_t(/* in */ int16_t val);
int32_t atomicincrement_int32_t(/* in */ int32_t val);
int64_t atomicincrement_int64_t(/* in */ int64_t val);
int8_t atomicdecrement_int8_t(/* in */ int8_t val);
int16_t atomicdecrement_int16_t(/* in */ int16_t val);
int32_t atomicdecrement_int32_t(/* in */ int32_t val);
int64_t atomicdecrement_int64_t(/* in */ int64_t val);

#else
#endif

#ifdef ECO_OS


#ifdef ECO_AVR8

#define atomicincrement_int8_t(val) \
{ \
    uint8_t s; \
    asm volatile( \
    "in %0, __SREG__" "\n\t" \
    "cli" "\n\t" \
    "ld __tmp_reg__, %a1" "\n\t" \
    "inc __tmp_reg__" "\n\t" \
    "st %a1, __tmp_reg__" "\n\t" \
    "out __SREG__, %0" "\n\t" \
    : "=&r" (s) \
    : "e" (val) \
    : "memory" \
    ); \
}

#define atomicincrement_int16_t(val) \
{ \
    uint8_t s; \
    asm volatile( \
    "in %0, __SREG__" "\n\t" \
    "cli" "\n\t" \
    "push zh" "\n\t" \
    "push zl" "\n\t" \
    "ld r24, z+" "\n\t" \
    "ld r25, z+" "\n\t" \
    "adiw r24, 1" "\n\t" \
    "pop zl" "\n\t" \
    "pop zh" "\n\t" \
    "st z+, r24" "\n\t" \
    "st z+, r25" "\n\t" \
    "out __SREG__, %0" "\n\t" \
    : "=&r" (s) \
    : "z" (val) \
    : "memory" \
    ); \
}

#define atomicincrement_int32_t(val) \
{ \
    uint8_t s; \
    asm volatile( \
    "in %0, __SREG__" "\n\t" \
    "cli" "\n\t" \
    "push zh" "\n\t" \
    "push zl" "\n\t" \
    "ld r24, z+" "\n\t" \
    "ld r25, z+" "\n\t" \
    "ld r26, z+" "\n\t" \
    "ld r27, z+" "\n\t" \
    "adiw r24, 1" "\n\t" \
    "adc r26, R1" "\n\t" \
    "adc r27, R1" "\n\t" \
    "pop zl" "\n\t" \
    "pop zh" "\n\t" \
    "st z+, r24" "\n\t" \
    "st z+, r25" "\n\t" \
    "st z+, r26" "\n\t" \
    "st z+, r27" "\n\t" \
    "out __SREG__, %0" "\n\t" \
    : "=&r" (s) \
    : "z" (val) \
    : "memory" \
    ); \
}

#define atomicincrement_int64_t(val) \
{ \
    uint8_t s; \
    asm volatile( \
    "in %0, __SREG__" "\n\t" \
    "cli" "\n\t" \
    "push zh" "\n\t" \
    "push zl" "\n\t" \
    "ld r24, z+" "\n\t" \
    "ld r25, z+" "\n\t" \
    "ld r26, z+" "\n\t" \
    "ld r27, z+" "\n\t" \
    "ld r28, z+" "\n\t" \
    "ld r29, z+" "\n\t" \
    "ld r18, z+" "\n\t" \
    "ld r19, z+" "\n\t" \
    "mov r30, r18" "\n\t" \
    "mov r31, r19" "\n\t" \
    "adiw r24, 1" "\n\t" \
    "adc r26, R1" "\n\t" \
    "adc r27, R1" "\n\t" \
    "adc r28, R1" "\n\t" \
    "adc r29, R1" "\n\t" \
    "adc r30, R1" "\n\t" \
    "adc r31, R1" "\n\t" \
    "mov r18, r30" "\n\t" \
    "mov r19, r31" "\n\t" \
    "pop zl" "\n\t" \
    "pop zh" "\n\t" \
    "st z+, r24" "\n\t" \
    "st z+, r25" "\n\t" \
    "st z+, r26" "\n\t" \
    "st z+, r27" "\n\t" \
    "st z+, r28" "\n\t" \
    "st z+, r29" "\n\t" \
    "st z+, r18" "\n\t" \
    "st z+, r19" "\n\t" \
    "out __SREG__, %0" "\n\t" \
    : "=&r" (s) \
    : "z" (val) \
    : "memory" \
    ); \
}

#define atomicdecrement_int8_t(val) \
{ \
    uint8_t s; \
    asm volatile( \
    "in %0, __SREG__" "\n\t" \
    "cli" "\n\t" \
    "ld __tmp_reg__, %a1" "\n\t" \
    "dec __tmp_reg__" "\n\t" \
    "st %a1, __tmp_reg__" "\n\t" \
    "out __SREG__, %0" "\n\t" \
    : "=&r" (s) \
    : "e" (val) \
    : "memory" \
    ); \
}

#define atomicdecrement_int16_t(val) \
{ \
    uint8_t s; \
    asm volatile( \
    "in %0, __SREG__" "\n\t" \
    "cli" "\n\t" \
    "push zh" "\n\t" \
    "push zl" "\n\t" \
    "ld r24, z+" "\n\t" \
    "ld r25, z+" "\n\t" \
    "sbiw r24, 1" "\n\t" \
    "pop zl" "\n\t" \
    "pop zh" "\n\t" \
    "st z+, r24" "\n\t" \
    "st z+, r25" "\n\t" \
    "out __SREG__, %0" "\n\t" \
    : "=&r" (s) \
    : "z" (val) \
    : "memory" \
    ); \
}

#define atomicdecrement_int32_t(val) \
{ \
    uint8_t s; \
    asm volatile( \
    "in %0, __SREG__" "\n\t" \
    "cli" "\n\t" \
    "push zh" "\n\t" \
    "push zl" "\n\t" \
    "ld r24, z+" "\n\t" \
    "ld r25, z+" "\n\t" \
    "ld r26, z+" "\n\t" \
    "ld r27, z+" "\n\t" \
    "sbiw r24, 1" "\n\t" \
    "sbc r26, R1" "\n\t" \
    "sbc r27, R1" "\n\t" \
    "pop zl" "\n\t" \
    "pop zh" "\n\t" \
    "st z+, r24" "\n\t" \
    "st z+, r25" "\n\t" \
    "st z+, r26" "\n\t" \
    "st z+, r27" "\n\t" \
    "out __SREG__, %0" "\n\t" \
    : "=&r" (s) \
    : "z" (val) \
    : "memory" \
    ); \
}

#define atomicdecrement_int64_t(val) \
{ \
    uint8_t s; \
    asm volatile( \
    "in %0, __SREG__" "\n\t" \
    "cli" "\n\t" \
    "push zh" "\n\t" \
    "push zl" "\n\t" \
    "ld r24, z+" "\n\t" \
    "ld r25, z+" "\n\t" \
    "ld r26, z+" "\n\t" \
    "ld r27, z+" "\n\t" \
    "ld r28, z+" "\n\t" \
    "ld r29, z+" "\n\t" \
    "ld r18, z+" "\n\t" \
    "ld r19, z+" "\n\t" \
    "mov r30, r18" "\n\t" \
    "mov r31, r19" "\n\t" \
    "sbiw r24, 1" "\n\t" \
    "sbc r26, R1" "\n\t" \
    "sbc r27, R1" "\n\t" \
    "sbc r28, R1" "\n\t" \
    "sbc r29, R1" "\n\t" \
    "sbc r30, R1" "\n\t" \
    "sbc r31, R1" "\n\t" \
    "mov r18, r30" "\n\t" \
    "mov r19, r31" "\n\t" \
    "pop zl" "\n\t" \
    "pop zh" "\n\t" \
    "st z+, r24" "\n\t" \
    "st z+, r25" "\n\t" \
    "st z+, r26" "\n\t" \
    "st z+, r27" "\n\t" \
    "st z+, r28" "\n\t" \
    "st z+, r29" "\n\t" \
    "st z+, r18" "\n\t" \
    "st z+, r19" "\n\t" \
    "out __SREG__, %0" "\n\t" \
    : "=&r" (s) \
    : "z" (val) \
    : "memory" \
    ); \
}

#elif ECO_AARCH64

#define atomicincrement_int64_t(val) \
{ \
    unsigned long tmp; \
    int result; \
    asm volatile( \
        "1: ldaxr   %w0, [%3]\n" \
        "   add     %w0, %w0, %w4\n" \
        "   stlxr   %w1, %w0, [%3]\n" \
        "   cbnz    %w1, 1b" \
        : "=&r" (result), "=&r" (tmp), "+o" (val) \
        : "r" (&val), "Ir" (1) \
        : "cc"); \
}

#define atomicdecrement_int64_t(val) \
{ \
    unsigned long tmp; \
    int result; \
    asm volatile( \
        "1: ldaxr   %w0, [%3]\n" \
        "   sub     %w0, %w0, %w4\n" \
        "   stlxr   %w1, %w0, [%3]\n" \
        "   cbnz    %w1, 1b" \
        : "=&r" (result), "=&r" (tmp), "+o" (val) \
        : "r" (&val), "Ir" (i) \
        : "cc"); \
}

#else

//#warning Atomic operation not defined

#define atomicincrement_int8_t(val) \
    (int8_t)((*val)++)
#define atomicincrement_int16_t(val) \
    (int16_t)((*val)++)
#define atomicincrement_int32_t(val) \
    (int32_t)((*val)++)
#define atomicincrement_int64_t(val) \
    (int64_t)((*val)++)
#define atomicdecrement_int16_t(val) \
    (int16_t)((*val)--)
#define atomicdecrement_int32_t(val) \
    (int32_t)((*val)--)
#define atomicdecrement_int64_t(val) \
    (int64_t)((*val)--)

#endif

#elif ECO_WINDOWS

#pragma warning( disable : 4995 )
#include <intrin.h>

#pragma intrinsic (_InterlockedIncrement)

#define atomicincrement_int8_t(val) \
    (int8_t)_InterlockedIncrement16(val)
#define atomicincrement_int16_t(val) \
    (int16_t)_InterlockedIncrement16(val)
#define atomicincrement_int32_t(val) \
    (int32_t)_InterlockedIncrement(val)
#define atomicincrement_int64_t(val) \
    (int64_t)_InterlockedIncrement64(val)
#define atomicdecrement_int8_t(val) \
    (int8_t)_InterlockedDecrement16(val)
#define atomicdecrement_int16_t(val) \
    (int16_t)_InterlockedDecrement16(val)
#define atomicdecrement_int32_t(val) \
    (int32_t)_InterlockedDecrement(val)
#define atomicdecrement_int64_t(val) \
    (int64_t)_InterlockedDecrement64(val)

#elif ECO_LINUX

#define atomicincrement_int8_t(val) \
    (int8_t)__atomic_add_fetch (val, 1, __ATOMIC_SEQ_CST)
#define atomicincrement_int16_t(val) \
    (int16_t)__atomic_add_fetch (val, 1, __ATOMIC_SEQ_CST)
#define atomicincrement_int32_t(val) \
    (int32_t)__atomic_add_fetch (val, 1, __ATOMIC_SEQ_CST)
#define atomicincrement_int64_t(val) \
    (int64_t)__atomic_add_fetch (val, 1, __ATOMIC_SEQ_CST)
#define atomicdecrement_int8_t(val) \
    (int8_t)__atomic_sub_fetch (val, 1, __ATOMIC_SEQ_CST)
#define atomicdecrement_int16_t(val) \
    (int16_t)__atomic_sub_fetch (val, 1, __ATOMIC_SEQ_CST)
#define atomicdecrement_int32_t(val) \
    (int32_t)__atomic_sub_fetch (val, 1, __ATOMIC_SEQ_CST)
#define atomicdecrement_int64_t(val) \
    (int64_t)__atomic_sub_fetch (val, 1, __ATOMIC_SEQ_CST)

#elif ECO_ANDROID

#define atomicincrement_int8_t(val) \
    (int8_t)__atomic_add_fetch (val, 1, __ATOMIC_SEQ_CST)
#define atomicincrement_int16_t(val) \
    (int16_t)__atomic_add_fetch (val, 1, __ATOMIC_SEQ_CST)
#define atomicincrement_int32_t(val) \
    (int32_t)__atomic_add_fetch (val, 1, __ATOMIC_SEQ_CST)
#define atomicincrement_int64_t(val) \
    (int64_t)__atomic_add_fetch (val, 1, __ATOMIC_SEQ_CST)
#define atomicdecrement_int8_t(val) \
    (int8_t)__atomic_sub_fetch (val, 1, __ATOMIC_SEQ_CST)
#define atomicdecrement_int16_t(val) \
    (int16_t)__atomic_sub_fetch (val, 1, __ATOMIC_SEQ_CST)
#define atomicdecrement_int32_t(val) \
    (int32_t)__atomic_sub_fetch (val, 1, __ATOMIC_SEQ_CST)
#define atomicdecrement_int64_t(val) \
    (int64_t)__atomic_sub_fetch (val, 1, __ATOMIC_SEQ_CST)

#elif ECO_APPLE

#if TARGET_OS_MAC
#include <libkern/OSAtomic.h>
#else
#import <libkern/OSAtomic.h>
#endif

#define atomicincrement_int8_t(val) \
    (int8_t)OSAtomicIncrement32(val)
#define atomicincrement_int16_t(val) \
    (int16_t)OSAtomicIncrement32(val)
#define atomicincrement_int32_t(val) \
    (int32_t)OSAtomicIncrement32(val)
#define atomicincrement_int64_t(val) \
    (int64_t)OSAtomicIncrement64(val)
#define atomicdecrement_int8_t(val) \
    (int8_t)OSAtomicDecrement32(val)
#define atomicdecrement_int16_t(val) \
    (int16_t)OSAtomicDecrement32(val)
#define atomicdecrement_int32_t(val) \
    (int32_t)OSAtomicDecrement32(val)
#define atomicdecrement_int64_t(val) \
    (int64_t)OSAtomicDecrement64(val)

#else

//#warning Atomic operation not defined

#define atomicincrement_int8_t(val) \
    (int8_t)((*val)++)
#define atomicincrement_int16_t(val) \
    (int16_t)((*val)++)
#define atomicincrement_int32_t(val) \
    (int32_t)((*val)++)
#define atomicincrement_int64_t(val) \
    (int64_t)((*val)++)
#define atomicdecrement_int16_t(val) \
    (int16_t)((*val)--)
#define atomicdecrement_int32_t(val) \
    (int32_t)((*val)--)
#define atomicdecrement_int64_t(val) \
    (int64_t)((*val)--)

#endif

#endif /* __ECO_ATOMIC_H__ */
