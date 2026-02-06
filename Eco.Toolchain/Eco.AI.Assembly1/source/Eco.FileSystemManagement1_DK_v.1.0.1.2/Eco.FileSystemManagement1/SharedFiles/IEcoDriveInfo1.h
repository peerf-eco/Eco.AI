/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoDriveInfo1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoDriveInfo1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2017 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_DRIVE_INFO_1_H__
#define __I_ECO_DRIVE_INFO_1_H__

#include "IEcoBase1.h"

/* IEcoDriveInfo1 IID = {00000000-0000-0000-0000-C00000000106} */
#ifndef __IID_IEcoDriveInfo1
static const UGUID IID_IEcoDriveInfo1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x01, 0x06} };
#endif /* __IID_IEcoDriveInfo1 */

typedef struct IEcoDriveInfo1* IEcoDriveInfo1Ptr_t;

typedef struct IEcoDriveInfo1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoDriveInfo1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoDriveInfo1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoDriveInfo1Ptr_t me);

    /* IEcoDriveInfo1 */
    UGUID* (ECOCALLMETHOD *get_Id)(/* in */ IEcoDriveInfo1Ptr_t me);

} IEcoDriveInfo1VTbl, *IEcoDriveInfo1VTblPtr;

interface IEcoDriveInfo1 {
    struct IEcoDriveInfo1VTbl *pVTbl;
} IEcoDriveInfo1;

#endif /* __I_ECO_DRIVE_INFO_1_H__ */
