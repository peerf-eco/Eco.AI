/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   CEcoAIEngine1
 * </summary>
 *
 * <description>
 *   This header describes the implementation of the CEcoAIEngine1 component
 * </description>
 *
 * <author>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </author>
 *
 */

#ifndef __C_ECOAIENGINE1_H__
#define __C_ECOAIENGINE1_H__

#include "IEcoAIEngine1.h"
#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"

typedef struct CEcoAIEngine1_EADFB777* CEcoAIEngine1_EADFB777Ptr_t;

typedef struct CEcoAIEngine1_EADFB777 {

    /* IEcoAIEngine1 interface function table */
    IEcoAIEngine1VTbl* m_pVTblIEcoAIEngine1;


    /* Instance initialization */
    int16_t (ECOCALLMETHOD *Init)(/*in*/ CEcoAIEngine1_EADFB777Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem);
    /* Instance creation */
    int16_t (ECOCALLMETHOD *Create)(/*in*/ CEcoAIEngine1_EADFB777Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoUnknownPtr_t pIUnkOuter);
    /* Deletion */
    void (ECOCALLMETHOD *Delete)(/*in*/ CEcoAIEngine1_EADFB777Ptr_t pCMe);


    /* Reference counter */
    uint32_t m_cRef;

    /* Interface for memory operations */
    IEcoMemoryAllocator1* m_pIMem;

    /* System interface */
    IEcoSystem1* m_pISys;

    /* Instance data */
    char_t* m_Name;

} CEcoAIEngine1_EADFB777;

#endif /* __C_ECOAIENGINE1_H__ */
