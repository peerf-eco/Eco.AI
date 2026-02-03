/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoTimeC89
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoTimeC89
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

#ifndef __I_ECO_TIME_C89_HPP__
#define __I_ECO_TIME_C89_HPP__

#include "IEcoBase1.hpp"

#ifdef ECO_OS
#ifndef __ECO_TIME_H__

#define CLK_TCK  1000

#ifndef NULL
#define NULL ((void *)0)
#endif 

#ifndef ECO_CLOCK_T_DEFINED
typedef long clock_t;
#define ECO_CLOCK_T_DEFINED
#endif 

#ifndef ECO_TIME_T_DEFINED
typedef long time_t;
#define ECO_TIME_T_DEFINED
#endif 

#ifndef ECO_SIZE_T_DEFINED
typedef unsigned int size_t;
#define ECO_SIZE_T_DEFINED
#endif 

#ifndef ECO_TM_DEFINED
struct tm {
    int tm_sec;     /* seconds after the minute - [0,59] */
    int tm_min;     /* minutes after the hour - [0,59] */
    int tm_hour;    /* hours since midnight - [0,23] */
    int tm_mday;    /* day of the month - [1,31] */
    int tm_mon;     /* months since January - [0,11] */
    int tm_year;    /* years since 1900 */
    int tm_wday;    /* days since Sunday - [0,6] */
    int tm_yday;    /* days since January 1 - [0,365] */
    int tm_isdst;   /* daylight savings time flag */
};
#define ECO_TM_DEFINED
#endif 

#endif
#endif

/* IEcoTimeC89 IID = {00000000-0000-0000-0000-890000007101} */
#ifndef __IID_IEcoTimeC89
static const UGUID IID_IEcoTimeC89 = {0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x89, 0x00, 0x00, 0x00, 0x71, 0x01}};
#endif /* __IID_IEcoTimeC89 */

interface IEcoTimeC89 : public IEcoUnknown {
public:

    /* IEcoTimeC89 */
    virtual clock_t ECOCALLMETHOD clock(/* in*/ void) = 0;
    virtual double ECOCALLMETHOD difftime(/* in */ time_t time1, time_t time0) = 0;
    virtual time_t ECOCALLMETHOD mktime(/* in */ struct tm *timeptr) = 0;
    virtual time_t ECOCALLMETHOD time(/* in */ time_t *timer) = 0;
    virtual char* ECOCALLMETHOD asctime(/* in */ const struct tm *timeptr) = 0;
    virtual char* ECOCALLMETHOD ctime(/* in */ const time_t *timer) = 0;
    virtual struct tm* ECOCALLMETHOD gmtime(/* in */ const time_t *timer) = 0;
    virtual struct tm* ECOCALLMETHOD localtime(/* in */ const time_t *timer) = 0;
    virtual size_t ECOCALLMETHOD strftime(/* in */ char *s, size_t maxsize, const char *format, const struct tm *timeptr) = 0;

};

#endif /* __I_ECO_TIME_C89_HPP__ */
