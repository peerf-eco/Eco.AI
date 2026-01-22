/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   IdEcoONNX1
 * </summary>
 *
 * <description>
 *   This header describes the interface IEcoONNX1
 * </description>
 *
 * <reference>
 *
 * </reference>
 *
 * <author>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </author>
 *
 */

#ifndef __I_ECOONNX1_H__
#define __I_ECOONNX1_H__

#include "IEcoBase1.h"

/* IEcoONNX1 IID = {39FE96C5-2B8D-4B46-B2E3-76F069EE7A11} */
#ifndef __IID_IEcoONNX1
static const UGUID IID_IEcoONNX1 = {0x01, 0x10, {0x39, 0xFE, 0x96, 0xC5, 0x2B, 0x8D, 0x4B, 0x46, 0xB2, 0xE3, 0x76, 0xF0, 0x69, 0xEE, 0x7A, 0x11}};
#endif /* __IID_IEcoONNX1 */

typedef struct IEcoONNX1* IEcoONNX1Ptr_t;

typedef struct IEcoONNX1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoONNX1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoONNX1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoONNX1Ptr_t me);

    /* IEcoONNX1 */
    int16_t (ECOCALLMETHOD *MyFunction)(/* in */ IEcoONNX1Ptr_t me, /* in */ char_t* Name, /* out */ char_t** CopyName);

} IEcoONNX1VTbl, *IEcoONNX1VTblPtr_t;

interface IEcoONNX1 {
    struct IEcoONNX1VTbl *pVTbl;
} IEcoONNX1;


#endif /* __I_ECOONNX1_H__ */

