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

#ifndef __I_ECO_DATETIME_1_HPP__
#define __I_ECO_DATETIME_1_HPP__

#include "IEcoBase1.hpp"

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

interface IEcoDateTime1 : public IEcoUnknown {

    /* IEcoDateTime1 */
    virtual IEcoDateTime1* ECOCALLMETHOD Now(/* in */void) = 0;
    virtual IEcoDateTime1* ECOCALLMETHOD Clone(/* in */void) = 0;
    virtual ECOTIMEVAL* ECOCALLMETHOD get_SystemTime(/* in */void) = 0;
    virtual void ECOCALLMETHOD set_SystemTime(/* in */ ECOTIMEVAL* value) = 0;
    virtual int32_t ECOCALLMETHOD get_TimeOfDaySec(/* in */void) = 0;
    virtual int32_t ECOCALLMETHOD get_TimeOfDayUSec(/* in */void) = 0;
    virtual char_t* ECOCALLMETHOD ToString(/* in */void) = 0;
    virtual char_t* ECOCALLMETHOD ToStringFormat(/* in */ char_t *format) = 0;

};

#endif /* __I_ECO_DATETIME_1_HPP__ */
