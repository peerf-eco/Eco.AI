/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoSystem1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейса IEcoSystem первого поколения
 *   Интерфейс IEcoSystem является основной точкой инициализации инфраструктуры Eco,
 *   построенной по технологии COM, для исользования в приложениях и библиотеках
 * 
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_SYSTEM_1_H__
#define __I_ECO_SYSTEM_1_H__

#include "IEcoBase1.h"

/* x86 */

/* IEcoSystem_x86_16 GID = 00000000-0000-0000-0000-000000CD0100 */
#ifndef __GID_IEcoSystem_x86_16
static const UGUID GID_IEcoSystem_x86_16 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xCD, 0x01, 0x00} };
#endif /* __GID_IEcoSystem_x86_16 */

/* IEcoSystem_x86_32 GID = 00000000-0000-0000-0000-000014C00200 */
#ifndef __GID_IEcoSystem_x86_32
static const UGUID GID_IEcoSystem_x86_32 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x14, 0xC0, 0x02, 0x00} };
#endif /* __GID_IEcoSystem_x86_32 */

/* IEcoSystem_x86_64 GID = 00000000-0000-0000-0000-000086640300 */
#ifndef __GID_IEcoSystem_x86_64
static const UGUID GID_IEcoSystem_x86_64 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x86, 0x64, 0x03, 0x00} };
#endif /* __GID_IEcoSystem_x86_64 */

/* RISC-V */

/* IEcoSystem_RV32 GID = 00000000-0000-0000-0000-000050320100 */
#ifndef __GID_IEcoSystem_RV32
static const UGUID GID_IEcoSystem_RV32 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x50, 0x32, 0x01, 0x00} };
#endif /* __GID_IEcoSystem_RV32 */

/* IEcoSystem_RV64 GID = 00000000-0000-0000-0000-000050640200 */
#ifndef __GID_IEcoSystem_RV64
static const UGUID GID_IEcoSystem_RV64 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x50, 0x64, 0x02, 0x00} };
#endif /* __GID_IEcoSystem_RV64 */

/* IEcoSystem_RV128 GID = 00000000-0000-0000-0000-000051280300 */
#ifndef __GID_IEcoSystem_RV128
static const UGUID GID_IEcoSystem_RV128 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x51, 0x28, 0x03, 0x00} };
#endif /* __GID_IEcoSystem_RVx128 */

/* ARM/AArch */

/* IEcoSystem_ARM GID = 00000000-0000-0000-0000-000001С20100 */
#ifndef __GID_IEcoSystem_ARM
static const UGUID GID_IEcoSystem_ARM = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0xC2, 0x01, 0x00} };
#endif /* __GID_IEcoSystem_ARM */

/* IEcoSystem_AARCH32 GID = 00000000-0000-0000-0000-000001С40200 */
#ifndef __GID_IEcoSystem_AARCH32
static const UGUID GID_IEcoSystem_AARCH32 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0xC4, 0x02, 0x00} };
#endif /* __GID_IEcoSystem_AARCH32 */

/* IEcoSystem_AARCH64 GID = 00000000-0000-0000-0000-0000AA640300 */
#ifndef __GID_IEcoSystem_AARCH64
static const UGUID GID_IEcoSystem_AARCH64 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xAA, 0x64, 0x03, 0x00} };
#endif /* __GID_IEcoSystem_AARCH64 */

/* MIPS */

/* IEcoSystem_MIPS GID = 00000000-0000-0000-0000-000003660100 */
#ifndef __GID_IEcoSystem_MIPS
static const UGUID GID_IEcoSystem_MIPS = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0x66, 0x01, 0x00} };
#endif /* __GID_IEcoSystem_MIPS */

/* IEcoSystem_MIPS64 GID = 00000000-0000-0000-0000-000003660200 */
#ifndef __GID_IEcoSystem_MIPS64
static const UGUID GID_IEcoSystem_MIPS64 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0x66, 0x02, 0x00} };
#endif /* __GID_IEcoSystem_MIPS64 */


/* AVR8 */

/* IEcoSystem_AVR GID = 00000000-0000-0000-0000-000000530100 */
#ifndef __GID_IEcoSystem_AVR
static const UGUID GID_IEcoSystem_AVR = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x53, 0x01, 0x00} };
#endif /* __GID_IEcoSystem_AVR */

/* IEcoSystem_AVRe GID = 00000000-0000-0000-0000-000000530200 */
#ifndef __GID_IEcoSystem_AVRe
static const UGUID GID_IEcoSystem_AVRe = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x53, 0x02, 0x00} };
#endif /* __GID_IEcoSystem_AVRe */


#ifdef ECO_OS

#ifdef ECO_X86_16

#define GID_IEcoSystem1 GID_IEcoSystem_x86_16

#define GID_IEcoSystem GID_IEcoSystem_x86_16

#elif ECO_X86_32

#define GID_IEcoSystem1 GID_IEcoSystem_x86_16
#define GID_IEcoSystem2 GID_IEcoSystem_x86_32

#define GID_IEcoSystem GID_IEcoSystem_x86_32

#elif ECO_X86_64

#define GID_IEcoSystem1 GID_IEcoSystem_x86_16
#define GID_IEcoSystem2 GID_IEcoSystem_x86_32
#define GID_IEcoSystem3 GID_IEcoSystem_x86_64

#define GID_IEcoSystem GID_IEcoSystem_x86_64

#elif ECO_RISCV_32

#define GID_IEcoSystem1 GID_IEcoSystem_RV32

#define GID_IEcoSystem GID_IEcoSystem_RV32

#elif ECO_RISCV_64

#define GID_IEcoSystem1 GID_IEcoSystem_RV32
#define GID_IEcoSystem2 GID_IEcoSystem_RV64

#define GID_IEcoSystem GID_IEcoSystem_RV64

#elif ECO_RISCV_128

#define GID_IEcoSystem1 GID_IEcoSystem_RV32
#define GID_IEcoSystem2 GID_IEcoSystem_RV64
#define GID_IEcoSystem3 GID_IEcoSystem_RV128

#define GID_IEcoSystem GID_IEcoSystem_RV128

#elif ECO_MIPS

#define GID_IEcoSystem1 GID_IEcoSystem_MIPS

#define GID_IEcoSystem GID_IEcoSystem_MIPS

#elif ECO_MIPS64

#define GID_IEcoSystem1 GID_IEcoSystem_MIPS
#define GID_IEcoSystem2 GID_IEcoSystem_MIPS64

#define GID_IEcoSystem GID_IEcoSystem_MIPS64

#elif ECO_AARCH32

#define GID_IEcoSystem1 GID_IEcoSystem_ARM
#define GID_IEcoSystem2 GID_IEcoSystem_AARCH32

#define GID_IEcoSystem GID_IEcoSystem_AARCH32

#elif ECO_AARCH64

#define GID_IEcoSystem1 GID_IEcoSystem_ARM
#define GID_IEcoSystem2 GID_IEcoSystem_AARCH32
#define GID_IEcoSystem3 GID_IEcoSystem_AARCH64

#define GID_IEcoSystem GID_IEcoSystem_AARCH64

#elif ECO_AVR

#define GID_IEcoSystem1 GID_IEcoSystem_AVR

#define GID_IEcoSystem GID_IEcoSystem_AVR

#elif ECO_AVR_E

#define GID_IEcoSystem1 GID_IEcoSystem_AVR
#define GID_IEcoSystem2 GID_IEcoSystem_AVRe

#define GID_IEcoSystem GID_IEcoSystem_AVRe

#else
#error Please define the architecture
#endif

#elif ECO_WINDOWS

#ifdef ECO_X86_32

#define GID_IEcoSystem1 GID_IEcoSystem_x86_16
#define GID_IEcoSystem2 GID_IEcoSystem_x86_32
#define GID_IEcoSystem3 GID_IEcoSystem_x86_64

#define GID_IEcoSystem GID_IEcoSystem_x86_32

#elif ECO_X86_64

#define GID_IEcoSystem1 GID_IEcoSystem_x86_16
#define GID_IEcoSystem2 GID_IEcoSystem_x86_32
#define GID_IEcoSystem3 GID_IEcoSystem_x86_64

#define GID_IEcoSystem GID_IEcoSystem_x86_64

#else
#error Please define the architecture
#endif

#elif ECO_LINUX

#ifdef ECO_X86_32

#define GID_IEcoSystem1 GID_IEcoSystem_x86_16
#define GID_IEcoSystem2 GID_IEcoSystem_x86_32
#define GID_IEcoSystem3 GID_IEcoSystem_x86_64

#define GID_IEcoSystem GID_IEcoSystem_x86_32

#elif ECO_X86_64

#define GID_IEcoSystem1 GID_IEcoSystem_x86_16
#define GID_IEcoSystem2 GID_IEcoSystem_x86_32
#define GID_IEcoSystem3 GID_IEcoSystem_x86_64

#define GID_IEcoSystem GID_IEcoSystem_x86_64

#elif ECO_AARCH32

#define GID_IEcoSystem1 GID_IEcoSystem_ARM
#define GID_IEcoSystem2 GID_IEcoSystem_AARCH32

#define GID_IEcoSystem GID_IEcoSystem_AARCH32

#elif ECO_AARCH64

#define GID_IEcoSystem1 GID_IEcoSystem_ARM
#define GID_IEcoSystem2 GID_IEcoSystem_AARCH32
#define GID_IEcoSystem3 GID_IEcoSystem_AARCH64

#define GID_IEcoSystem GID_IEcoSystem_AARCH64

#elif ECO_RISCV_32

#define GID_IEcoSystem1 GID_IEcoSystem_RV32

#define GID_IEcoSystem GID_IEcoSystem_RV32

#elif ECO_RISCV_64

#define GID_IEcoSystem1 GID_IEcoSystem_RV32
#define GID_IEcoSystem2 GID_IEcoSystem_RV64

#define GID_IEcoSystem GID_IEcoSystem_RV64

#elif ECO_RISCV_128

#define GID_IEcoSystem1 GID_IEcoSystem_RV32
#define GID_IEcoSystem2 GID_IEcoSystem_RV64
#define GID_IEcoSystem3 GID_IEcoSystem_RV128

#define GID_IEcoSystem GID_IEcoSystem_RV128

#else
#error Please define the architecture
#endif

#elif ECO_APPLE

#ifdef ECO_X86_32

#define GID_IEcoSystem1 GID_IEcoSystem_x86_16
#define GID_IEcoSystem2 GID_IEcoSystem_x86_32
#define GID_IEcoSystem3 GID_IEcoSystem_x86_64

#define GID_IEcoSystem GID_IEcoSystem_x86_32

#elif ECO_X86_64

#define GID_IEcoSystem1 GID_IEcoSystem_x86_16
#define GID_IEcoSystem2 GID_IEcoSystem_x86_32
#define GID_IEcoSystem3 GID_IEcoSystem_x86_64

#define GID_IEcoSystem GID_IEcoSystem_x86_64

#elif ECO_AARCH32

#define GID_IEcoSystem1 GID_IEcoSystem_ARM
#define GID_IEcoSystem2 GID_IEcoSystem_AARCH32
#define GID_IEcoSystem3 GID_IEcoSystem_AARCH64

#define GID_IEcoSystem GID_IEcoSystem_AARCH32

#elif ECO_AARCH64

#define GID_IEcoSystem1 GID_IEcoSystem_ARM
#define GID_IEcoSystem2 GID_IEcoSystem_AARCH32
#define GID_IEcoSystem3 GID_IEcoSystem_AARCH64

#define GID_IEcoSystem GID_IEcoSystem_AARCH64

#elif ECO_UNIVERSAL

#ifdef __x86_64__

#define GID_IEcoSystem1 GID_IEcoSystem_x86_16
#define GID_IEcoSystem2 GID_IEcoSystem_x86_32
#define GID_IEcoSystem3 GID_IEcoSystem_x86_64

#define GID_IEcoSystem GID_IEcoSystem_x86_64

#elif __arm64__

#define GID_IEcoSystem1 GID_IEcoSystem_ARM
#define GID_IEcoSystem2 GID_IEcoSystem_AARCH32
#define GID_IEcoSystem3 GID_IEcoSystem_AARCH64

#define GID_IEcoSystem GID_IEcoSystem_AARCH64

#endif

#else
#error Please define the architecture
#endif

#elif ECO_ANDROID

#ifdef ECO_X86_32

#define GID_IEcoSystem1 GID_IEcoSystem_x86_16
#define GID_IEcoSystem2 GID_IEcoSystem_x86_32
#define GID_IEcoSystem3 GID_IEcoSystem_x86_64

#define GID_IEcoSystem GID_IEcoSystem_x86_32

#elif ECO_X86_64

#define GID_IEcoSystem1 GID_IEcoSystem_x86_16
#define GID_IEcoSystem2 GID_IEcoSystem_x86_32
#define GID_IEcoSystem3 GID_IEcoSystem_x86_64

#define GID_IEcoSystem GID_IEcoSystem_x86_64

#elif ECO_MIPS

#define GID_IEcoSystem1 GID_IEcoSystem_MIPS
#define GID_IEcoSystem2 GID_IEcoSystem_MIPS64

#define GID_IEcoSystem GID_IEcoSystem_MIPS

#elif ECO_MIPS64

#define GID_IEcoSystem1 GID_IEcoSystem_MIPS
#define GID_IEcoSystem2 GID_IEcoSystem_MIPS64

#define GID_IEcoSystem GID_IEcoSystem_MIPS64

#elif ECO_ARM

#define GID_IEcoSystem1 GID_IEcoSystem_ARM
#define GID_IEcoSystem2 GID_IEcoSystem_AARCH32
#define GID_IEcoSystem3 GID_IEcoSystem_AARCH64

#define GID_IEcoSystem GID_IEcoSystem_ARM

#elif ECO_AARCH32

#define GID_IEcoSystem1 GID_IEcoSystem_ARM
#define GID_IEcoSystem2 GID_IEcoSystem_AARCH32
#define GID_IEcoSystem3 GID_IEcoSystem_AARCH64

#define GID_IEcoSystem GID_IEcoSystem_AARCH32

#elif ECO_AARCH64

#define GID_IEcoSystem1 GID_IEcoSystem_ARM
#define GID_IEcoSystem2 GID_IEcoSystem_AARCH32
#define GID_IEcoSystem3 GID_IEcoSystem_AARCH64

#define GID_IEcoSystem GID_IEcoSystem_AARCH64

#else
#error Please define the architecture
#endif

#else
#error Please define the platform
#endif

#ifndef ECO_I_ECO_SYSTEM_1_PTR_T_DEFINED
typedef struct IEcoSystem1* IEcoSystem1Ptr_t;
#define ECO_I_ECO_SYSTEM_1_PTR_T_DEFINED
#endif

typedef struct IEcoSystem1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoSystem1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoSystem1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoSystem1Ptr_t me);

    /* IEcoSystem1 */
    void (ECOCALLMETHOD *set_Data)(/* in */ IEcoSystem1Ptr_t me, /* in */ voidptr_t pv);
    void* (ECOCALLMETHOD *get_Data)(/* in */ IEcoSystem1Ptr_t me);

} IEcoSystem1VTbl, *IEcoSystem1VTblPtr;

interface IEcoSystem1 {
    struct IEcoSystem1VTbl *pVTbl;
} IEcoSystem1;

#endif /* __I_ECO_SYSTEM_1_H__ */
