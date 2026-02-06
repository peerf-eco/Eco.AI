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

#ifndef __I_ECO_MATH_C89_HPP__
#define __I_ECO_MATH_C89_HPP__

#include "IEcoBase1.hpp"

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

interface IEcoMathC89 : public IEcoUnknown {
public:
    /* IEcoMathC89 */
    virtual double ECOCALLMETHOD acos(/* in */ double x) = 0;
    virtual double ECOCALLMETHOD asin(/* in */ double x) = 0;
    virtual double ECOCALLMETHOD atan(/* in */ double x) = 0;
    virtual double ECOCALLMETHOD atan2(/* in */ double y, /* in */ double x) = 0;
    virtual double ECOCALLMETHOD cos(/* in */ double x) = 0;
    virtual double ECOCALLMETHOD sin(/* in */ double x) = 0;
    virtual double ECOCALLMETHOD tan(/* in */ double x) = 0;
    virtual double ECOCALLMETHOD cosh(/* in */ double x) = 0;
    virtual double ECOCALLMETHOD sinh(/* in */ double x) = 0;
    virtual double ECOCALLMETHOD tanh(/* in */ double x) = 0;
    virtual double ECOCALLMETHOD exp(/* in */ double x) = 0;
    virtual double ECOCALLMETHOD frexp(/* in */ double value, /* in */ int *exp) = 0;
    virtual double ECOCALLMETHOD ldexp(/* in */ double x, /* in */ int exp) = 0;
    virtual double ECOCALLMETHOD log(/* in */ double x) = 0;
    virtual double ECOCALLMETHOD log10(/* in */ double x) = 0;
    virtual double ECOCALLMETHOD modf(/* in */ double value, /* in */ double *iptr) = 0;
    virtual double ECOCALLMETHOD pow(/* in */ double x, /* in */ double y) = 0;
    virtual double ECOCALLMETHOD sqrt(/* in */ double x) = 0;
    virtual double ECOCALLMETHOD ceil(/* in */ double x) = 0;
    virtual double ECOCALLMETHOD fabs(/* in */ double x) = 0;
    virtual double ECOCALLMETHOD floor(/* in */ double x) = 0;
    virtual double ECOCALLMETHOD fmod(/* in */ double x, /* in */ double y) = 0;

};

#endif /* __I_ECO_MATH_C89_HPP__ */
