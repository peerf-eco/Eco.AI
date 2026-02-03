/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoMutex1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoMutex1
 * </описание>
 *
 * <ссылка>
 *
 * </ссылка>
 *
 * <автор>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_MUTEX_1_H__
#define __I_ECO_MUTEX_1_H__

#include "IEcoBase1.h"

/* IEcoMutex1 IID = {DD292B8D-750B-4A3C-BB8D-316D609A398A} */
#ifndef __IID_IEcoMutex1
static const UGUID IID_IEcoMutex1 = {0x01, 0x10, {0xDD, 0x29, 0x2B, 0x8D, 0x75, 0x0B, 0x4A, 0x3C, 0xBB, 0x8D, 0x31, 0x6D, 0x60, 0x9A, 0x39, 0x8A} };
#endif /* __IID_IEcoMutex1 */

typedef struct IEcoMutex1* IEcoMutex1Ptr_t;

typedef struct IEcoMutex1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoMutex1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoMutex1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoMutex1Ptr_t me);

    /* IEcoMutex1Ptr_t */
    void (ECOCALLMETHOD *Lock)(/* in */ IEcoMutex1Ptr_t me);
    void (ECOCALLMETHOD *UnLock)(/* in */ IEcoMutex1Ptr_t me);

} IEcoMutex1VTbl, *IEcoMutex1VTblPtr;

interface IEcoMutex1 {
    struct IEcoMutex1VTbl *pVTbl;
} IEcoMutex1;

#endif /* __I_ECO_MUTEX_1_H__ */
