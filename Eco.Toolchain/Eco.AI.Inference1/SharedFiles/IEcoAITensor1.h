/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   IEcoAITensor1
 * </summary>
 *
 * <description>
 *   This header describes the interface IEcoAITensor1
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

#ifndef __I_ECO_AI_TENSOR_1_H__
#define __I_ECO_AI_TENSOR_1_H__

#include "IEcoBase1.h"

/* IEcoAITensor1 IID = {B704AD3D-E013-43B5-8515-00D87DEE0A93} */
#ifndef __IID_IEcoAITensor1
static const UGUID IID_IEcoAITensor1 = {0x01, 0x10, {0xB7, 0x04, 0xAD, 0x3D, 0xE0, 0x13, 0x43, 0xB5, 0x85, 0x15, 0x00, 0xD8, 0x7D, 0xEE, 0x0A, 0x93}};
#endif /* __IID_IEcoAITensor1 */

typedef struct IEcoAITensor1* IEcoAITensor1Ptr_t;

typedef struct IEcoAITensor1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoAITensor1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoAITensor1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoAITensor1Ptr_t me);

    /* IEcoAITensor1 */
    /* Доступ к низкоуровневой математике */
    int16_t (ECOCALLMETHOD *get_Matrix)(IEcoAITensor1Ptr_t me, struct IEcoMatrix1** ppIMatrix);
    
    /* Геометрия тензора */
    uint8_t (ECOCALLMETHOD *get_Rank)(IEcoAITensor1Ptr_t me);
    int16_t (ECOCALLMETHOD *get_Shape)(IEcoAITensor1Ptr_t me, uint32_t* pDims, uint8_t maxDims);
    
    /* Управление состоянием (Init/Weights/Buffer) */
    uint8_t (ECOCALLMETHOD *get_Type)(IEcoAITensor1Ptr_t me); /* ECO_MATRIX_1_TYPE */
    char_t* (ECOCALLMETHOD *get_Name)(IEcoAITensor1Ptr_t me);
    
} IEcoAITensor1VTbl, *IEcoAITensor1VTblPtr_t;

interface IEcoAITensor1 {
    struct IEcoAITensor1VTbl *pVTbl;
} IEcoAITensor1;


#endif /* __I_ECO_AI_TENSOR_1_H__ */

