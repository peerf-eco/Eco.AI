/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   IdEcoHDF5
 * </summary>
 *
 * <description>
 *   This header describes the interface IEcoHDF5
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

#ifndef __I_ECOHDF5_H__
#define __I_ECOHDF5_H__

#include "IEcoBase1.h"

/* IEcoHDF5 IID = {BB451325-C050-44C1-BCC2-E929C4C9F6AB} */
#ifndef __IID_IEcoHDF5
static const UGUID IID_IEcoHDF5 = {0x01, 0x10, {0xBB, 0x45, 0x13, 0x25, 0xC0, 0x50, 0x44, 0xC1, 0xBC, 0xC2, 0xE9, 0x29, 0xC4, 0xC9, 0xF6, 0xAB}};
#endif /* __IID_IEcoHDF5 */

typedef struct IEcoHDF5* IEcoHDF5Ptr_t;

typedef struct IEcoHDF5VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoHDF5Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoHDF5Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoHDF5Ptr_t me);

    /* IEcoHDF5 */
    int16_t (ECOCALLMETHOD *MyFunction)(/* in */ IEcoHDF5Ptr_t me, /* in */ char_t* Name, /* out */ char_t** CopyName);

} IEcoHDF5VTbl, *IEcoHDF5VTblPtr_t;

interface IEcoHDF5 {
    struct IEcoHDF5VTbl *pVTbl;
} IEcoHDF5;


#endif /* __I_ECOHDF5_H__ */

