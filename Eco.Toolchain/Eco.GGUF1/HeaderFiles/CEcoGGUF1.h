/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   CEcoGGUF1
 * </summary>
 *
 * <description>
 *   This header describes the implementation of the CEcoGGUF1 component
 * </description>
 *
 * <author>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </author>
 *
 */

#ifndef __C_ECOGGUF1_H__
#define __C_ECOGGUF1_H__

#include "IEcoGGUF1.h"
#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"

typedef struct CEcoGGUF1_B24682B2* CEcoGGUF1_B24682B2Ptr_t;

typedef struct CEcoGGUF1_B24682B2 {

    /* IEcoGGUF1 interface function table */
    IEcoGGUF1VTbl* m_pVTblIEcoGGUF1;


    /* Instance initialization */
    int16_t (ECOCALLMETHOD *Init)(/*in*/ CEcoGGUF1_B24682B2Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem);
    /* Instance creation */
    int16_t (ECOCALLMETHOD *Create)(/*in*/ CEcoGGUF1_B24682B2Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoUnknownPtr_t pIUnkOuter);
    /* Deletion */
    void (ECOCALLMETHOD *Delete)(/*in*/ CEcoGGUF1_B24682B2Ptr_t pCMe);


    /* Reference counter */
    uint32_t m_cRef;

    /* Interface for memory operations */
    IEcoMemoryAllocator1* m_pIMem;

    /* System interface */
    IEcoSystem1* m_pISys;

    /* Instance data */
    char_t* m_Name;

} CEcoGGUF1_B24682B2;

#endif /* __C_ECOGGUF1_H__ */
