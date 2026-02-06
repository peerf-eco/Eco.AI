/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoDirectoryInfo1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoDirectoryInfo1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2017 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_DIRECTORY_INFO_1_H__
#define __I_ECO_DIRECTORY_INFO_1_H__

#include "IEcoBase1.h"

/* IEcoDirectoryInfo1 IID = {00000000-0000-0000-0000-C00000000108} */
#ifndef __IID_IEcoDirectoryInfo1
static const UGUID IID_IEcoDirectoryInfo1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x01, 0x08} };
#endif /* __IID_IEcoDirectoryInfo1 */

typedef struct IEcoDirectoryInfo1* IEcoDirectoryInfo1Ptr_t;

typedef struct IEcoDirectoryInfo1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoDirectoryInfo1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoDirectoryInfo1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoDirectoryInfo1Ptr_t me);

    /* IEcoDirectoryInfo1 */
    UGUID* (ECOCALLMETHOD *get_Id)(/* in */ IEcoDirectoryInfo1Ptr_t me);

} IEcoDirectoryInfo1VTbl, *IEcoDirectoryInfo1VTblPtr;

interface IEcoDirectoryInfo1 {
    struct IEcoDirectoryInfo1VTbl *pVTbl;
} IEcoDirectoryInfo1;

#endif /* __I_ECO_DIRECTORY_INFO_1_H__ */
