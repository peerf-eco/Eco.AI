/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoFileInfo1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoFileInfo1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2017 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_FILE_INFO_1_H__
#define __I_ECO_FILE_INFO_1_H__

#include "IEcoBase1.h"
//#include "IEcoDateTime1.h"

/* IEcoFileInfo1 IID = {00000000-0000-0000-0000-C00000000103} */
#ifndef __IID_IEcoFileInfo1
static const UGUID IID_IEcoFileInfo1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x01, 0x03} };
#endif /* __IID_IEcoFileInfo1 */

typedef struct IEcoFileInfo1* IEcoFileInfo1Ptr_t;

typedef struct IEcoFileInfo1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoFileInfo1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoFileInfo1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoFileInfo1Ptr_t me);

    /* IEcoFileInfo1 */
    UGUID* (ECOCALLMETHOD *get_Id)(/* in */ IEcoFileInfo1Ptr_t me);

} IEcoFileInfo1VTbl, *IEcoFileInfo1VTblPtr;

interface IEcoFileInfo1 {
    struct IEcoFileInfo1VTbl *pVTbl;
} IEcoFileInfo1;

#endif /* __I_ECO_FILE_INFO_1_H__ */
