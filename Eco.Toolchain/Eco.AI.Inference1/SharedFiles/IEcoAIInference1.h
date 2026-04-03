/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   IdEcoAIInference1
 * </summary>
 *
 * <description>
 *   This header describes the interface IEcoAIInference1
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

#ifndef __I_ECO_AI_INFERENCE_1_H__
#define __I_ECO_AI_INFERENCE_1_H__

#include "IEcoBase1.h"
#include "IEcoAIModel1.h"

/* IEcoAIInference1 IID = {5B86C037-BDDF-478E-839D-457A6A3C0624} */
#ifndef __IID_IEcoAIInference1
static const UGUID IID_IEcoAIInference1 = {0x01, 0x10, {0x5B, 0x86, 0xC0, 0x37, 0xBD, 0xDF, 0x47, 0x8E, 0x83, 0x9D, 0x45, 0x7A, 0x6A, 0x3C, 0x06, 0x24}};
#endif /* __IID_IEcoAIInference1 */

typedef struct IEcoAIInference1* IEcoAIInference1Ptr_t;

typedef struct IEcoAIInference1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoAIInference1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoAIInference1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoAIInference1Ptr_t me);

    /* IEcoAIInference1 */


    /* Загрузка/Сохранение (сериализация) */
    int16_t (ECOCALLMETHOD *Load)(IEcoAIInference1Ptr_t me, char_t* path);

     /* Привязка модели к движку */
    int16_t (ECOCALLMETHOD *Init)(IEcoAIInference1Ptr_t me, IEcoAIModel1* pIModel);

    /* РЕЖИМ 1: Полный запуск */
    int16_t (ECOCALLMETHOD *Run)(IEcoAIInference1Ptr_t me);

    /* РЕЖИМ 2: Пошаговое выполнение для отладки */
    int16_t (ECOCALLMETHOD *Step)(IEcoAIInference1Ptr_t me, struct IEcoGraph1Node** ppCurrentNode);
    int16_t (ECOCALLMETHOD *Reset)(IEcoAIInference1Ptr_t me);

    /* Установка Callback для мониторинга после каждого шага */
    int16_t (ECOCALLMETHOD *SetStepCallback)(IEcoAIInference1Ptr_t me, void (*callback)(struct IEcoGraph1Node* pNode));

} IEcoAIInference1VTbl, *IEcoAIInference1VTblPtr_t;

interface IEcoAIInference1 {
    struct IEcoAIInference1VTbl *pVTbl;
} IEcoAIInference1;


#endif /* __I_ECO_AI_INFERENCE_1_H__ */

