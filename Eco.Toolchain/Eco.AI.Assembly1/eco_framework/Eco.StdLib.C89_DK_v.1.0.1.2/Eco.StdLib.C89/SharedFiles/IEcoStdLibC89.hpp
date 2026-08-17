/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoStdLibC89
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoStdLibC89
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

#ifndef __I_ECO_STD_LIB_C89_HPP__
#define __I_ECO_STD_LIB_C89_HPP__

#include "IEcoBase1.hpp"

#ifdef ECO_OS
#ifndef __ECO_STDLIB_H__

#ifndef EXIT_FAILURE
#define EXIT_FAILURE    1
#define EXIT_SUCCESS    0
#endif

#ifndef MB_CUR_MAX
extern unsigned short ECO_MB_CUR_MAX;
#define MB_CUR_MAX ECO_MB_CUR_MAX
#endif

#ifndef NULL
#define NULL ((void *)0)
#endif

#ifndef RAND_MAX
#define RAND_MAX 0x7fff
#endif

#ifndef ECO_DIV_T_DEFINED

typedef struct div_t {
    int quot;
    int rem;
} div_t;

typedef struct ldiv_t {
    long quot;
    long rem;
} ldiv_t;

#define ECO_DIV_T_DEFINED
#endif

#ifndef ECO_SIZE_T_DEFINED
typedef unsigned int size_t;
#define ECO_SIZE_T_DEFINED
#endif

#ifndef ECO_WCHAR_T_DEFINED
typedef unsigned short wchar_t;
#define ECO_WCHAR_T_DEFINED
#endif

#endif
#endif

/* IEcoStdLibC89 IID = {00000000-0000-0000-0000-890000000101} */
#ifndef __IID_IEcoStdLibC89
static const UGUID IID_IEcoStdLibC89 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x89, 0x00, 0x00, 0x00, 0x01, 0x01}};
#endif /* __IID_IEcoStdLibC89 */

interface IEcoStdLibC89 : public IEcoUnknown {
public:
    /* IEcoStdLibC89 */
    virtual double ECOCALLMETHOD atof(/* in */ const char *nptr) = 0;
    virtual int ECOCALLMETHOD atoi(/* in */ const char *nptr) = 0;
    virtual long int ECOCALLMETHOD atol(/* in */ const char *nptr) = 0;
    virtual double ECOCALLMETHOD strtod(/* in */ const char *nptr, /* in */ char **endptr) = 0;
    virtual long int ECOCALLMETHOD strtol(/* in */ const char *nptr, /* in */ char **endptr, /* in */ int base) = 0;
    virtual unsigned long int ECOCALLMETHOD strtoul(/* in */ const char *nptr, /* in */ char **endptr, /* in */ int base) = 0;
    virtual int ECOCALLMETHOD rand(/* in*/ void) = 0;
    virtual void ECOCALLMETHOD srand(/* in */ unsigned int seed) = 0;
    virtual void* ECOCALLMETHOD calloc(/* in */ size_t nmemb, /* in */ size_t size) = 0;
    virtual void ECOCALLMETHOD free(/* in */ void *ptr) = 0;
    virtual void* ECOCALLMETHOD malloc(/* in */ size_t size) = 0;
    virtual void* ECOCALLMETHOD realloc(/* in */ void *ptr, /* in */ size_t size) = 0;
    virtual void ECOCALLMETHOD abort(/* in*/ void) = 0;
    virtual int ECOCALLMETHOD atexit(/* in */ void (ECOCDECLMETHOD *func)(void)) = 0;
    virtual void ECOCALLMETHOD exit(/* in */ int status) = 0;
    virtual char* ECOCALLMETHOD getenv(/* in */ const char *name) = 0;
    virtual int ECOCALLMETHOD system(/* in */ const char *string) = 0;
    virtual void* ECOCALLMETHOD bsearch(/* in */ const void *key, /* in */ const void *base, /* in */ size_t nmemb, /* in */ size_t size, /* in */ int (ECOCDECLMETHOD *compar)(const void *, const void *)) = 0;
    virtual void ECOCALLMETHOD qsort(/* in */ void *base, /* in */ size_t nmemb, /* in */ size_t size, /* in */ int (ECOCDECLMETHOD *compar)(const void *, const void *)) = 0;
    virtual int ECOCALLMETHOD abs(/* in */ int j) = 0;
    virtual div_t ECOCALLMETHOD div(/* in */ int numer, /* in */ int denom) = 0;
    virtual long int ECOCALLMETHOD labs(/* in */ long int j) = 0;
    virtual ldiv_t ECOCALLMETHOD ldiv(/* in */ long int numer, /* in */ long int denom) = 0;
    virtual int ECOCALLMETHOD mblen(/* in */ const char *s, /* in */ size_t n) = 0;
    virtual int ECOCALLMETHOD mbtowc(/* in */ wchar_t *pwc, const char *s, /* in */ size_t n) = 0;
    virtual int ECOCALLMETHOD wctomb(/* in */ char *s, /* in */ wchar_t wchar) = 0;
    virtual size_t ECOCALLMETHOD mbstowcs(/* in */ wchar_t *pwcs, /* in */ const char *s, /* in */ size_t n);
    virtual size_t ECOCALLMETHOD wcstombs(/* in */ char *s, /* in */ const wchar_t *pwcs, /* in */ size_t n);
};

#endif /* __I_ECO_STD_LIB_C89_HPP__ */
