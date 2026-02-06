/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoMathC89
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoMathC89
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

#ifndef __I_ECO_MATH_C89_H__
#define __I_ECO_MATH_C89_H__

#include "IEcoBase1.h"

#ifndef ECO_HUGE_VAL_DEFINED
#define HUGE_VAL 
#define ECO_HUGE_VAL_DEFINED
#endif

#ifndef ECO_DOUBLE_COMPLEX_T_DEFINED
typedef union ECO_DOUBLE_COMPLEX_T {
    struct {
        double real;
        double imaginary;
    } Part;
    double Value[2];
} ECO_DOUBLE_COMPLEX_T;
#define ECO_DOUBLE_COMPLEX_T_DEFINED
#endif

/* IEcoMathC89 IID = {EE823C32-2B86-470C-B4C9-D3760C0AF470} */
#ifndef __IID_IEcoMathC89
static const UGUID IID_IEcoMathC89 = {0x01, 0x10, {0xEE, 0x82, 0x3C, 0x32, 0x2B, 0x86, 0x47, 0x0C, 0xB4, 0xC9, 0xD3, 0x76, 0x0C, 0x0A, 0xF4, 0x70} };
#endif /* __IID_IEcoMathC89 */

typedef struct IEcoMathC89* IEcoMathC89Ptr_t;

typedef struct IEcoMathC89VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoMathC89Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoMathC89Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoMathC89Ptr_t me);

    /* IEcoMathC89 */
    double (ECOCALLMETHOD *acos)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x);
    double (ECOCALLMETHOD *asin)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x);
    double (ECOCALLMETHOD *atan)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x);
    double (ECOCALLMETHOD *atan2)(/* in */ IEcoMathC89Ptr_t me, /* in */ double y, /* in */ double x);
    double (ECOCALLMETHOD *cos)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x);
    double (ECOCALLMETHOD *sin)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x);
    double (ECOCALLMETHOD *tan)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x);
    double (ECOCALLMETHOD *cosh)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x);
    double (ECOCALLMETHOD *sinh)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x);
    double (ECOCALLMETHOD *tanh)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x);
    double (ECOCALLMETHOD *exp)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x);
    double (ECOCALLMETHOD *frexp)(/* in */ IEcoMathC89Ptr_t me, /* in */ double value, /* in */ int *exp);
    double (ECOCALLMETHOD *ldexp)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x, /* in */ int exp);
    double (ECOCALLMETHOD *log)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x);
    double (ECOCALLMETHOD *log10)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x);
    double (ECOCALLMETHOD *modf)(/* in */ IEcoMathC89Ptr_t me, /* in */ double value, /* in */ double *iptr);
    double (ECOCALLMETHOD *pow)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x, /* in */ double y);
    double (ECOCALLMETHOD *sqrt)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x);
    double (ECOCALLMETHOD *ceil)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x);
    double (ECOCALLMETHOD *fabs)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x);
    double (ECOCALLMETHOD *floor)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x);
    double (ECOCALLMETHOD *fmod)(/* in */ IEcoMathC89Ptr_t me, /* in */ double x, /* in */ double y);

} IEcoMathC89VTbl, *IEcoMathC89VTblPtr;

interface IEcoMathC89 {
    struct IEcoMathC89VTbl *pVTbl;
} IEcoMathC89;


#endif /* __I_ECO_MATH_C89_H__ */
