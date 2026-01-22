/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   IdEcoAIEngine1
 * </summary>
 *
 * <description>
 *   This header describes the interface IEcoAIEngine1
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

#ifndef __I_ECOAIENGINE1_H__
#define __I_ECOAIENGINE1_H__

#include "IEcoBase1.h"

/* IEcoAIEngine1 IID = {7490F220-211B-4743-9FF4-7D0C35D50588} */
#ifndef __IID_IEcoAIEngine1
static const UGUID IID_IEcoAIEngine1 = {0x01, 0x10, {0x74, 0x90, 0xF2, 0x20, 0x21, 0x1B, 0x47, 0x43, 0x9F, 0xF4, 0x7D, 0x0C, 0x35, 0xD5, 0x05, 0x88}};
#endif /* __IID_IEcoAIEngine1 */

typedef struct IEcoAIEngine1* IEcoAIEngine1Ptr_t;

typedef struct IEcoAIEngine1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoAIEngine1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoAIEngine1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoAIEngine1Ptr_t me);

    /* IEcoAIEngine1 */
    int16_t (ECOCALLMETHOD *MyFunction)(/* in */ IEcoAIEngine1Ptr_t me, /* in */ char_t* Name, /* out */ char_t** CopyName);

} IEcoAIEngine1VTbl, *IEcoAIEngine1VTblPtr_t;

interface IEcoAIEngine1 {
    struct IEcoAIEngine1VTbl *pVTbl;
} IEcoAIEngine1;


#endif /* __I_ECOAIENGINE1_H__ */

