/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   IEcoAIModel1
 * </summary>
 *
 * <description>
 *   This header describes the interface IEcoAIModel1
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

#ifndef __I_ECO_AI_MODEL_1_H__
#define __I_ECO_AI_MODEL_1_H__

#include "IEcoBase1.h"

/* IEcoAIModel1 IID = {A917977F-E603-45A9-B340-ABDC21BAC7E3} */
#ifndef __IID_IEcoAIModel1
static const UGUID IID_IEcoAIModel1 = {0x01, 0x10, {0xA9, 0x17, 0x97, 0x7F, 0xE6, 0x03, 0x45, 0xA9, 0xB3, 0x40, 0xAB, 0xDC, 0x21, 0xBA, 0xC7, 0xE3}};
#endif /* __IID_IEcoAIModel1 */

typedef struct IEcoAIModel1* IEcoAIModel1Ptr_t;

typedef struct IEcoAIModel1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoAIModel1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoAIModel1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoAIModel1Ptr_t me);

    /* IEcoAIModel1 */

    /* Доступ к графу для обхода или отладки */
    int16_t (ECOCALLMETHOD *get_Graph)(IEcoAIModel1Ptr_t me, struct IEcoGraph1** ppIGraph);
    
    /* Быстрый доступ к точкам входа/выхода */
    int16_t (ECOCALLMETHOD *get_Inputs)(IEcoAIModel1Ptr_t me, struct IEcoList1** ppInTensors);
    int16_t (ECOCALLMETHOD *get_Outputs)(IEcoAIModel1Ptr_t me, struct IEcoList1** ppOutTensors);

} IEcoAIModel1VTbl, *IEcoAIModel1VTblPtr_t;

interface IEcoAIModel1 {
    struct IEcoAIModel1VTbl *pVTbl;
} IEcoAIModel1;


#endif /* __I_ECO_AI_MODEL_1_H__ */

