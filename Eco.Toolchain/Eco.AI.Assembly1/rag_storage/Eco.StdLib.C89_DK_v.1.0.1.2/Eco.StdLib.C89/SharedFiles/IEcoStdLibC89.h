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

#ifndef __I_ECO_STD_LIB_C89_H__
#define __I_ECO_STD_LIB_C89_H__

#include "IEcoBase1.h"

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

typedef struct IEcoStdLibC89* IEcoStdLibC89Ptr_t;

typedef struct IEcoStdLibC89VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ const UGUID* riid, /* out */ void **ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoStdLibC89Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoStdLibC89Ptr_t me);

    /* IEcoStdLibC89 */
    double (ECOCALLMETHOD *atof)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ const char *nptr);
    int (ECOCALLMETHOD *atoi)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ const char *nptr);
    long int (ECOCALLMETHOD *atol)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ const char *nptr);
    double (ECOCALLMETHOD *strtod)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ const char *nptr, /* in */ char **endptr);
    long int (ECOCALLMETHOD *strtol)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ const char *nptr, /* in */ char **endptr, /* in */ int base);
    unsigned long int (ECOCALLMETHOD *strtoul)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ const char *nptr, /* in */ char **endptr, /* in */ int base);
    int (ECOCALLMETHOD *rand)(/* in */ IEcoStdLibC89Ptr_t me);
    void (ECOCALLMETHOD *srand)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ unsigned int seed);
    void* (ECOCALLMETHOD *calloc)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ size_t nmemb, /* in */ size_t size);
    void (ECOCALLMETHOD *free)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ void *ptr);
    void* (ECOCALLMETHOD *malloc)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ size_t size);
    void* (ECOCALLMETHOD *realloc)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ void *ptr, /* in */ size_t size);
    void (ECOCALLMETHOD *abort)(/* in */ IEcoStdLibC89Ptr_t me);
    int (ECOCALLMETHOD *atexit)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ void (ECOCDECLMETHOD *func)(void));
    void (ECOCALLMETHOD *exit)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ int status);
    char* (ECOCALLMETHOD *getenv)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ const char *name);
    int (ECOCALLMETHOD *system)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ const char *string);
    void* (ECOCALLMETHOD *bsearch)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ const void *key, /* in */ const void *base, /* in */ size_t nmemb, /* in */ size_t size, /* in */ int (ECOCDECLMETHOD *compar)(const void *, const void *));
    void (ECOCALLMETHOD *qsort)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ void *base, /* in */ size_t nmemb, /* in */ size_t size, /* in */ int (ECOCDECLMETHOD *compar)(const void *, const void *));
    int (ECOCALLMETHOD *abs)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ int j);
    div_t (ECOCALLMETHOD *div)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ int numer, /* in */ int denom);
    long int (ECOCALLMETHOD *labs)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ long int j);
    ldiv_t (ECOCALLMETHOD *ldiv)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ long int numer, /* in */ long int denom);
    int (ECOCALLMETHOD *mblen)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ const char *s, /* in */ size_t n);
    int (ECOCALLMETHOD *mbtowc)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ wchar_t *pwc, const char *s, /* in */ size_t n);
    int (ECOCALLMETHOD *wctomb)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ char *s, /* in */ wchar_t wchar);
    size_t (ECOCALLMETHOD *mbstowcs)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ wchar_t *pwcs, /* in */ const char *s, /* in */ size_t n);
    size_t (ECOCALLMETHOD *wcstombs)(/* in */ IEcoStdLibC89Ptr_t me, /* in */ char *s, /* in */ const wchar_t *pwcs, /* in */ size_t n);

} IEcoStdLibC89VTbl, *IEcoStdLibC89VTblPtr;

interface IEcoStdLibC89 {
    struct IEcoStdLibC89VTbl *pVTbl;
} IEcoStdLibC89;

#endif /* __I_ECO_STD_LIB_C89_H__ */
