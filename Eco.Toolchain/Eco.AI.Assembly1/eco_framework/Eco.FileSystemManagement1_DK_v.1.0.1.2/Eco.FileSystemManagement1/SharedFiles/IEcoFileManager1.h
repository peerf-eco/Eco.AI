/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoFileManager1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoFileManager1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_FILE_MANAGER_1_H__
#define __I_ECO_FILE_MANAGER_1_H__

#include "IEcoBase1.h"
#include "IEcoFile1.h"

/* IEcoFileManager1 IID = {00000000-0000-0000-0000-C00000000102} */
#ifndef __IID_IEcoFileManager1
static const UGUID IID_IEcoFileManager1 = {0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x01, 0x02} };
#endif /* __IID_IEcoFileManager1 */

typedef struct IEcoFileManager1* IEcoFileManager1Ptr_t;

typedef struct IEcoFileManager1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoFileManager1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoFileManager1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoFileManager1Ptr_t me);

    /* IEcoFileManager1 */
    IEcoFile1* (ECOCALLMETHOD *Create)(/* in */ IEcoFileManager1Ptr_t me, /* in */ char_t* pszName);
    IEcoFile1* (ECOCALLMETHOD *Open)(/* in */ IEcoFileManager1Ptr_t me, /* in */ char_t* pszName);
    int32_t (ECOCALLMETHOD *Close)(/* in */ IEcoFileManager1Ptr_t me, /* in */ IEcoFile1* pIFile);

} IEcoFileManager1VTbl, *IEcoFileManager1VTblPtr;

interface IEcoFileManager1 {
    struct IEcoFileManager1VTbl *pVTbl;
} IEcoFileManager1;

#endif /* __I_ECO_FILE_MANAGER_1_H__ */
