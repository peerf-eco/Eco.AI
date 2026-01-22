/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   CEcoHDF5
 * </summary>
 *
 * <description>
 *   This header describes the implementation of the CEcoHDF5 component
 * </description>
 *
 * <author>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </author>
 *
 */

#ifndef __C_ECOHDF5_H__
#define __C_ECOHDF5_H__

#include "IEcoHDF5.h"
#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"

typedef struct CEcoHDF5_0AAAA5F0* CEcoHDF5_0AAAA5F0Ptr_t;

typedef struct CEcoHDF5_0AAAA5F0 {

    /* IEcoHDF5 interface function table */
    IEcoHDF5VTbl* m_pVTblIEcoHDF5;


    /* Instance initialization */
    int16_t (ECOCALLMETHOD *Init)(/*in*/ CEcoHDF5_0AAAA5F0Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem);
    /* Instance creation */
    int16_t (ECOCALLMETHOD *Create)(/*in*/ CEcoHDF5_0AAAA5F0Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoUnknownPtr_t pIUnkOuter);
    /* Deletion */
    void (ECOCALLMETHOD *Delete)(/*in*/ CEcoHDF5_0AAAA5F0Ptr_t pCMe);


    /* Reference counter */
    uint32_t m_cRef;

    /* Interface for memory operations */
    IEcoMemoryAllocator1* m_pIMem;

    /* System interface */
    IEcoSystem1* m_pISys;

    /* Instance data */
    char_t* m_Name;

} CEcoHDF5_0AAAA5F0;

#endif /* __C_ECOHDF5_H__ */
