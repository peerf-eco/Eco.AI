/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoMathFFT1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoMathFFT1
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

#ifndef __I_ECO_MATH_FFT_1_HPP__
#define __I_ECO_MATH_FFT_1_HPP__

#include "IEcoBase1.hpp"

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

/* IEcoMathFFT1 IID = {A84A0702-41C8-4D68-AAEC-1575FBAFDE9E} */
#ifndef __IID_IEcoMathFFT1
static const UGUID IID_IEcoMathFFT1 = {0x01, 0x10, {0xA8, 0x4A, 0x07, 0x02, 0x41, 0xC8, 0x4D, 0x68, 0xAA, 0xEC, 0x15, 0x75, 0xFB, 0xAF, 0xDE, 0x9E} };
#endif /* __IID_IEcoMathFFT1 */

interface IEcoMathFFT1 : public IEcoUnknown {
public:
    /* IEcoMathFFT1 */
    virtual int16_t ECOCALLMETHOD fft(/* in */ ECO_DOUBLE_COMPLEX_T *X, /* in */ int16_t N, /* out */ ECO_DOUBLE_COMPLEX_T **Y) = 0;
    virtual int16_t ECOCALLMETHOD ifft(/* in */ ECO_DOUBLE_COMPLEX_T *X, /* in */ int16_t N, /* out */ ECO_DOUBLE_COMPLEX_T **Y) = 0;
    virtual int16_t ECOCALLMETHOD fft2(/* in */ ECO_DOUBLE_COMPLEX_T *X, /* in */ int16_t M, /* in */ int16_t N, /* out */ ECO_DOUBLE_COMPLEX_T **Y) = 0;
    virtual int16_t ECOCALLMETHOD ifft2(/* in */ ECO_DOUBLE_COMPLEX_T *X, /* in */ int16_t M, /* in */ int16_t N, /* out */ ECO_DOUBLE_COMPLEX_T **Y) = 0;

};

#endif /* __I_ECO_MATH_FFT_1_HPP__ */
