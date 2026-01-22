/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   IdEcoGGUF1
 * </summary>
 *
 * <description>
 *   This header describes the interface IEcoGGUF1
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

#ifndef __I_ECOGGUF1_H__
#define __I_ECOGGUF1_H__

#include "IEcoBase1.h"

/* IEcoGGUF1 IID = {E000F49A-E6F0-46F3-B930-52E45BB81629} */
#ifndef __IID_IEcoGGUF1
static const UGUID IID_IEcoGGUF1 = {0x01, 0x10, {0xE0, 0x00, 0xF4, 0x9A, 0xE6, 0xF0, 0x46, 0xF3, 0xB9, 0x30, 0x52, 0xE4, 0x5B, 0xB8, 0x16, 0x29}};
#endif /* __IID_IEcoGGUF1 */

typedef struct IEcoGGUF1* IEcoGGUF1Ptr_t;

typedef struct IEcoGGUF1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoGGUF1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoGGUF1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoGGUF1Ptr_t me);

    /* IEcoGGUF1 */
    int16_t (ECOCALLMETHOD *MyFunction)(/* in */ IEcoGGUF1Ptr_t me, /* in */ char_t* Name, /* out */ char_t** CopyName);

} IEcoGGUF1VTbl, *IEcoGGUF1VTblPtr_t;

interface IEcoGGUF1 {
    struct IEcoGGUF1VTbl *pVTbl;
} IEcoGGUF1;


#endif /* __I_ECOGGUF1_H__ */

