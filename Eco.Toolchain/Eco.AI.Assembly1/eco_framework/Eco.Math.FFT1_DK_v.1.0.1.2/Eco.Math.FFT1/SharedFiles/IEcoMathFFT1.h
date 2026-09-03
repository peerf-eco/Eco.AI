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

#ifndef __I_ECO_MATH_FFT_1_H__
#define __I_ECO_MATH_FFT_1_H__

#include "IEcoBase1.h"

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

typedef struct IEcoMathFFT1* IEcoMathFFT1Ptr_t;

typedef struct IEcoMathFFT1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoMathFFT1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoMathFFT1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoMathFFT1Ptr_t me);

    /* IEcoMathFFT1 */
    int16_t (ECOCALLMETHOD *fft)(/* in */ IEcoMathFFT1Ptr_t me, /* in */ ECO_DOUBLE_COMPLEX_T *X, /* in */ int16_t N, /* out */ ECO_DOUBLE_COMPLEX_T **Y);
    int16_t (ECOCALLMETHOD *ifft)(/* in */ IEcoMathFFT1Ptr_t me, /* in */ ECO_DOUBLE_COMPLEX_T *X, /* in */ int16_t N, /* out */ ECO_DOUBLE_COMPLEX_T **Y);
    int16_t (ECOCALLMETHOD *fft2)(/* in */ IEcoMathFFT1Ptr_t me, /* in */ ECO_DOUBLE_COMPLEX_T *X, /* in */ int16_t M, /* in */ int16_t N, /* out */ ECO_DOUBLE_COMPLEX_T **Y);
    int16_t (ECOCALLMETHOD *ifft2)(/* in */ IEcoMathFFT1Ptr_t me, /* in */ ECO_DOUBLE_COMPLEX_T *X, /* in */ int16_t M, /* in */ int16_t N, /* out */ ECO_DOUBLE_COMPLEX_T **Y);

} IEcoMathFFT1VTbl, *IEcoMathFFT1VTblPtr;

interface IEcoMathFFT1 {
    struct IEcoMathFFT1VTbl *pVTbl;
} IEcoMathFFT1;


#endif /* __I_ECO_MATH_FFT_1_H__ */
