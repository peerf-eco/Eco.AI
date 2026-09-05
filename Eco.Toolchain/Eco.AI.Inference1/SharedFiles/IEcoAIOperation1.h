/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   IEcoAIOperation1
 * </summary>
 *
 * <description>
 *   This header describes the interface IEcoAIOperation1
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

#ifndef __I_ECO_AI_OPERATION_1_H__
#define __I_ECO_AI_OPERATION_1_H__

#include "IEcoBase1.h"

/* IEcoAIOperation1 IID = {BB46C0B6-9C9D-4A63-A1DF-5A01E3CC4B0A} */
#ifndef __IID_IEcoAIOperation1
static const UGUID IID_IEcoAIOperation1 = {0x01, 0x10, {0xBB, 0x46, 0xC0, 0xB6, 0x9C, 0x9D, 0x4A, 0x63, 0xA1, 0xDF, 0x5A, 0x01, 0xE3, 0xCC, 0x4B, 0x0A}};
#endif /* __IID_IEcoAIOperation1 */

typedef struct IEcoAIOperation1* IEcoAIOperation1Ptr_t;

typedef struct IEcoAIOperation1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoAIOperation1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoAIOperation1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoAIOperation1Ptr_t me);

    /* IEcoAIOperation1 */
    
     /* Выполнить операцию над списками тензоров (ребер графа) */
    int16_t (ECOCALLMETHOD *Execute)(IEcoAIOperation1Ptr_t me, struct IEcoList1* pInEdges, struct IEcoList1* pOutEdges);
    
    /* Работа с атрибутами (например, alpha для Gemm или axis для Softmax) */
    int16_t (ECOCALLMETHOD *GetAttribute)(IEcoAIOperation1Ptr_t me, char_t* attrName, void* pValue);
    int16_t (ECOCALLMETHOD *SetAttribute)(IEcoAIOperation1Ptr_t me, char_t* attrName, void* pValue);

} IEcoAIOperation1VTbl, *IEcoAIOperation1VTblPtr_t;

interface IEcoAIOperation1 {
    struct IEcoAIOperation1VTbl *pVTbl;
} IEcoAIOperation1;


#endif /* __I_ECO_AI_OPERATION_1_H__ */

