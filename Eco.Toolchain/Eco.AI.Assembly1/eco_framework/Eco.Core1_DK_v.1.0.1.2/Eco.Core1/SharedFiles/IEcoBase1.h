/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoBase1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает базовые определения данных
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_BASE_1_H__
#define __I_ECO_BASE_1_H__

/* Поддержка зависимостей */
#include "ErrEcoCodes.h"
#include "depend.h"

#ifndef INTERFACE_DEFINED
#undef interface
#define interface typedef struct
#define INTERFACE_DEFINED
#endif

#ifndef UGUID_DEFINED
typedef struct UGUID UGUID;
#define UGUID_DEFINED
#endif

#ifndef ECO_GUID128_DEFINED
typedef struct UGUID {
    byte_t Preamble;
    byte_t Length;
    byte_t Data[16];
} GUID128;
#define ECO_GUID128_DEFINED
#endif

#ifdef UGUID_UTILITY

#define IsEqualUGUID(rguid1, rguid2)  \
    ((((byte_t *) rguid1)[0] == ((byte_t *) rguid2)[0]) &&   \
    (((byte_t *) rguid1)[1] == ((byte_t *) rguid2)[1]) &&    \
    (((byte_t *) rguid1)[2] == ((byte_t *) rguid2)[2]) &&    \
    (((byte_t *) rguid1)[3] == ((byte_t *) rguid2)[3]) &&    \
    (((byte_t *) rguid1)[4] == ((byte_t *) rguid2)[4]) &&    \
    (((byte_t *) rguid1)[5] == ((byte_t *) rguid2)[5]) &&    \
    (((byte_t *) rguid1)[6] == ((byte_t *) rguid2)[6]) &&    \
    (((byte_t *) rguid1)[7] == ((byte_t *) rguid2)[7]) &&    \
    (((byte_t *) rguid1)[8] == ((byte_t *) rguid2)[8]) &&    \
    (((byte_t *) rguid1)[9] == ((byte_t *) rguid2)[9]) &&    \
    (((byte_t *) rguid1)[10] == ((byte_t *) rguid2)[10]) &&    \
    (((byte_t *) rguid1)[11] == ((byte_t *) rguid2)[11]) &&    \
    (((byte_t *) rguid1)[12] == ((byte_t *) rguid2)[12]) &&    \
    (((byte_t *) rguid1)[13] == ((byte_t *) rguid2)[13]) &&    \
    (((byte_t *) rguid1)[14] == ((byte_t *) rguid2)[14]) &&    \
    (((byte_t *) rguid1)[15] == ((byte_t *) rguid2)[15]) &&    \
    (((byte_t *) rguid1)[16] == ((byte_t *) rguid2)[16]) &&    \
    (((byte_t *) rguid1)[17] == ((byte_t *) rguid2)[17]))

#endif

/* IEcoUnknown IID = 00000000-0000-0000-0000-0000000000AA */
#ifndef __IID_IEcoUnknown
static const UGUID IID_IEcoUnknown = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xAA} };
#endif /* __IID_IEcoUnknown */

#ifndef ECO_I_ECO_UNKNOWN_PTR_T_DEFINED
typedef struct IEcoUnknown* IEcoUnknownPtr_t;
#define ECO_I_ECO_UNKNOWN_PTR_T_DEFINED
#endif

typedef struct IEcoUnknownVTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoUnknownPtr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoUnknownPtr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoUnknownPtr_t me);

} IEcoUnknownVTbl;

interface IEcoUnknown {
    struct IEcoUnknownVTbl* pVTbl;
} IEcoUnknown;

/* IEcoComponentFactory IID = 00000000-0000-0000-0000-000000000055 */
#ifndef __IID_IEcoComponentFactory
static const UGUID IID_IEcoComponentFactory = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x55} };
#endif /* __IID_IEcoComponentFactory */

#ifndef ECO_I_ECO_COMPONENT_FACTORY_PTR_T_DEFINED
typedef struct IEcoComponentFactory* IEcoComponentFactoryPtr_t;
#define ECO_I_ECO_COMPONENT_FACTORY_PTR_T_DEFINED
#endif

typedef struct IEcoComponentFactoryVTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoComponentFactoryPtr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoComponentFactoryPtr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoComponentFactoryPtr_t me);

    int16_t (ECOCALLMETHOD *Alloc)(/* in */ IEcoComponentFactoryPtr_t me, /* in */ IEcoUnknownPtr_t pISystem, /* in */ IEcoUnknownPtr_t pIUnknownOuter, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    int16_t (ECOCALLMETHOD *Init)(/* in */ IEcoComponentFactoryPtr_t me, /* in */ IEcoUnknownPtr_t pISystem, /* in */ voidptr_t pv);
    char_t* (ECOCALLMETHOD *get_Name)(/* in */ IEcoComponentFactoryPtr_t me);
    char_t* (ECOCALLMETHOD *get_Version)(/* in */ IEcoComponentFactoryPtr_t me);
    char_t* (ECOCALLMETHOD *get_Manufacturer)(/* in */ IEcoComponentFactoryPtr_t me);

} IEcoComponentFactoryVTbl;

interface IEcoComponentFactory {
    struct IEcoComponentFactoryVTbl* pVTbl;
} IEcoComponentFactory;

/* Определение функции и структуры создания экземпляра для фабрики компонентов */
typedef int16_t (ECOCALLMETHOD *CreateInstance)(voidptr_t, voidptr_t, voidptr_t*);

/* Определение функции инициализации экземпляра для фабрики компонентов */
typedef int16_t (ECOCALLMETHOD *InitInstance)(voidptr_t, voidptr_t);

#endif /* __I_ECO_BASE_1_H__ */
