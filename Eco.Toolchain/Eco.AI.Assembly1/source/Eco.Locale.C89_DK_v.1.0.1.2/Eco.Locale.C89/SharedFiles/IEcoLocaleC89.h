/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoLocaleC89
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoLocaleC89
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

#ifndef __I_ECO_LOCALE_C89_H__
#define __I_ECO_LOCALE_C89_H__

#include "IEcoBase1.h"

#ifdef ECO_OS

#ifndef NULL
#define NULL ((void *)0)
#endif

#ifndef LC_COLLATE
#define LC_ALL      0
#define LC_COLLATE  1
#define LC_CTYPE    2
#define LC_MONETARY 3
#define LC_NUMERIC  4
#define LC_TIME     5

#define LC_MIN      LC_ALL
#define LC_MAX      LC_TIME
#endif

#ifndef ECO_LCONV_DEFINED
struct lconv {
    char *decimal_point;
    char *thousands_sep;
    char *grouping;
    char *int_curr_symbol;
    char *currency_symbol;
    char *mon_decimal_point;
    char *mon_thousands_sep;
    char *mon_grouping;
    char *positive_sign;
    char *negative_sign;
    char int_frac_digits;
    char frac_digits;
    char p_cs_precedes;
    char p_sep_by_space;
    char n_cs_precedes;
    char n_sep_by_space;
    char p_sign_posn;
    char n_sign_posn;
    };
#define ECO_LCONV_DEFINED
#endif

#endif

/* IEcoLocaleC89 IID = {00000000-0000-0000-0000-89000000B101} */
#ifndef __IID_IEcoLocaleC89
static const UGUID IID_IEcoLocaleC89 = {0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x89, 0x00, 0x00, 0x00, 0xB1, 0x01}};
#endif /* __IID_IEcoLocaleC89 */

typedef struct IEcoLocaleC89* IEcoLocaleC89Ptr_t;

typedef struct IEcoLocaleC89VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoLocaleC89Ptr_t me, /* in */ const UGUID* riid, /* out */ void **ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoLocaleC89Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoLocaleC89Ptr_t me);

    /* IEcoLocaleC89 */
    char* (ECOCALLMETHOD *setlocale)(/* in */ IEcoLocaleC89Ptr_t me, /* in */ int category, /* in */ const char *locale);
    struct lconv* (ECOCALLMETHOD *localeconv)(/* in */ IEcoLocaleC89Ptr_t me);

} IEcoLocaleC89VTbl, *IEcoLocaleC89VTblPtr;

interface IEcoLocaleC89 {
    struct IEcoLocaleC89VTbl *pVTbl;
} IEcoLocaleC89;


#endif /* __I_ECO_LOCALE_C89_H__ */
