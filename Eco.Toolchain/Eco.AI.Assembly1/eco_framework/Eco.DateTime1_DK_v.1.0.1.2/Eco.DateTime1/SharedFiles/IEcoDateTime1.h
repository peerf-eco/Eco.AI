/*
 * <кодировка символов>
 *   Cyrillic (Windows) - Codepage 1251
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoDateTime1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoDateTime1
 * </описание>
 *
 * <ссылка>
 *
 * </ссылка>
 *
 * <автор>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_DATETIME_1_H__
#define __I_ECO_DATETIME_1_H__

#include "IEcoBase1.h"

/* Совместимость  с tm */
typedef struct ECODATETIME {
    int16_t tm_sec;     /* seconds after the minute - [0,59] */
    int16_t tm_min;     /* minutes after the hour - [0,59] */
    int16_t tm_hour;    /* hours since midnight - [0,23] */
    int16_t tm_mday;    /* day of the month - [1,31] */
    int16_t tm_mon;     /* months since January - [0,11] */
    int16_t tm_year;    /* years since 1900 */
    int16_t tm_wday;    /* days since Sunday - [0,6] */
    int16_t tm_yday;    /* days since January 1 - [0,365] */
    int16_t tm_isdst;   /* daylight savings time flag */
} ECODATETIME;

/* Совместимость  с timeval */
typedef struct ECOTIMEVAL {
    int32_t tv_sec;     /* seconds */
    int32_t tv_usec;    /* and microseconds */
} ECOTIMEVAL;

/* IEcoDateTime1 IID = {CA5A4E0E-7EEB-4CA9-92C6-22043FFA07BC} */
#ifndef __IID_IEcoDateTime1
static const UGUID IID_IEcoDateTime1 = {0x01, 0x10, {0xCA, 0x5A, 0x4E, 0x0E, 0x7E, 0xEB, 0x4C, 0xA9, 0x92, 0xC6, 0x22, 0x04, 0x3F, 0xFA, 0x07, 0xBC} };
#endif /* __IID_IEcoDateTime1 */

typedef struct IEcoDateTime1* IEcoDateTime1Ptr_t;

typedef struct IEcoDateTime1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoDateTime1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoDateTime1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoDateTime1Ptr_t me);

    /* IEcoDateTime1 */
    IEcoDateTime1Ptr_t (ECOCALLMETHOD *Now)(/* in */ IEcoDateTime1Ptr_t me);
    IEcoDateTime1Ptr_t (ECOCALLMETHOD *Clone)(/* in */ IEcoDateTime1Ptr_t me);
    ECOTIMEVAL* (ECOCALLMETHOD *get_SystemTime)(/* in */ IEcoDateTime1Ptr_t me);
    void (ECOCALLMETHOD *set_SystemTime)(/* in */ IEcoDateTime1Ptr_t me, /* in */ ECOTIMEVAL* value);
    int32_t (ECOCALLMETHOD *get_TimeOfDaySec)(/* in */ IEcoDateTime1Ptr_t me);
    int32_t (ECOCALLMETHOD *get_TimeOfDayUSec)(/* in */ IEcoDateTime1Ptr_t me);
    char_t* (ECOCALLMETHOD *ToString)(/* in */ IEcoDateTime1Ptr_t me);
    char_t* (ECOCALLMETHOD *ToStringFormat)(/* in */ IEcoDateTime1Ptr_t me, /* in */ char_t *format);

} IEcoDateTime1VTbl, *IEcoDateTime1VTblPtr;

interface IEcoDateTime1 {
    struct IEcoDateTime1VTbl *pVTbl;
} IEcoDateTime1;

#endif /* __I_ECO_DATETIME_1_H__ */
