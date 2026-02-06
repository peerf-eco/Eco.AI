/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoDirectoryManager1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoDirectoryManager1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2017 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_DIRECTORY_MANAGER_1_H__
#define __I_ECO_DIRECTORY_MANAGER_1_H__

#include "IEcoBase1.h"
#include "IEcoDirectoryInfo1.h"

/* IEcoDirectoryManager1 IID = {00000000-0000-0000-0000-C00000000107} */
#ifndef __IID_IEcoDirectoryManager1
static const UGUID IID_IEcoDirectoryManager1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x01, 0x07} };
#endif /* __IID_IEcoDirectoryManager1 */

typedef struct IEcoDirectoryManager1* IEcoDirectoryManager1Ptr_t;

typedef struct IEcoDirectoryManager1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoDirectoryManager1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoDirectoryManager1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoDirectoryManager1Ptr_t me);

    /* IEcoDirectoryManager1 */
    IEcoDirectoryInfo1* (ECOCALLMETHOD *Create)(/* in */ IEcoDirectoryManager1Ptr_t me, /* in */ char_t* pszName);
    int32_t (ECOCALLMETHOD *Delete)(/* in */ IEcoDirectoryManager1Ptr_t me, /* in */ char_t* pszName);

} IEcoDirectoryManager1VTbl, *IEcoDirectoryManager1VTblPtr;

interface IEcoDirectoryManager1 {
    struct IEcoDirectoryManager1VTbl *pVTbl;
} IEcoDirectoryManager1;

#endif /* __I_ECO_DIRECTORY_MANAGER_1_H__ */
