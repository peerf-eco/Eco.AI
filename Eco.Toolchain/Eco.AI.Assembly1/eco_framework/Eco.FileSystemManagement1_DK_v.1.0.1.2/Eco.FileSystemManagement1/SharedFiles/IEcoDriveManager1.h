/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoDriveManager1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoDriveManager1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2017 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_DRIVE_MANAGER_1_H__
#define __I_ECO_DRIVE_MANAGER_1_H__

#include "IEcoBase1.h"
#include "IEcoDriveInfo1.h"

/* IEcoDriveManager1 IID = {00000000-0000-0000-0000-C00000000105} */
#ifndef __IID_IEcoDriveManager1
static const UGUID IID_IEcoDriveManager1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x01, 0x05} };
#endif /* __IID_IEcoDriveManager1 */

typedef struct IEcoDriveManager1* IEcoDriveManager1Ptr_t;

typedef struct IEcoDriveManager1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoDriveManager1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoDriveManager1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoDriveManager1Ptr_t me);

    /* IEcoDriveManager1 */
    IEcoDriveInfo1* (ECOCALLMETHOD *get_Drive)(/* in */ IEcoDriveManager1Ptr_t me, /* in */ char_t* pszName);

} IEcoDriveManager1VTbl, *IEcoDriveManager1VTblPtr;

interface IEcoDriveManager1 {
    struct IEcoDriveManager1VTbl *pVTbl;
} IEcoDriveManager1;

#endif /* __I_ECO_DIRECTORY_MANAGER_1_H__ */
