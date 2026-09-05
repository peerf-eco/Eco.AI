/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   CEcoAIInference1Tensor
 * </summary>
 *
 * <description>
 *   This header describes the implementation of the CEcoAIInference1Tensor component
 * </description>
 *
 * <author>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </author>
 *
 */

#ifndef __C_ECO_AI_INFERENCE_1_TENSOR_H__
#define __C_ECO_AI_INFERENCE_1_TENSOR_H__

#include "IEcoAITensor1.h"
#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"

typedef struct CEcoAIInference1Tensor_D82986D3* CEcoAIInference1Tensor_D82986D3Ptr_t;

typedef struct CEcoAIInference1Tensor_D82986D3 {

    /* IEcoAITensor1 interface function table */
    IEcoAITensor1VTbl* m_pVTblITensor;


    /* Instance initialization */
    int16_t (ECOCALLMETHOD *Init)(/*in*/ CEcoAIInference1Tensor_D82986D3Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem);
    /* Instance creation */
    int16_t (ECOCALLMETHOD *Create)(/*in*/ CEcoAIInference1Tensor_D82986D3Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoUnknownPtr_t pIUnkOuter);
    /* Deletion */
    void (ECOCALLMETHOD *Delete)(/*in*/ CEcoAIInference1Tensor_D82986D3Ptr_t pCMe);


    /* Reference counter */
    uint32_t m_cRef;

    /* Interface for memory operations */
    IEcoMemoryAllocator1* m_pIMem;

    /* System interface */
    IEcoSystem1* m_pISys;

    /* Instance data */
    char_t* m_Name;

} CEcoAIInference1Tensor_D82986D3;

#endif /* __C_ECO_AI_INFERENCE_1_TENSOR_H__ */
