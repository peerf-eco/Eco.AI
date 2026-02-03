/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoFileSystemManagement1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов файловой системы
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2017 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_FILE_SYSTEM_MANAGEMENT_1_H__
#define __I_ECO_FILE_SYSTEM_MANAGEMENT_1_H__

#include "IEcoBase1.h"
#include "IEcoFileManager1.h"
#include "IEcoDirectoryManager1.h"
#include "IEcoDriveManager1.h"

/* IEcoFileSystemManagement1 IID = {00000000-0000-0000-0000-C00000000101} */
#ifndef __IID_IEcoFileSystemManagement1
static const UGUID IID_IEcoFileSystemManagement1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x01, 0x01} };
#endif /* __IID_IEcoFileSystemManagement1 */

typedef struct IEcoFileSystemManagement1* IEcoFileSystemManagement1Ptr_t;

typedef struct IEcoFileSystemManagement1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoFileSystemManagement1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoFileSystemManagement1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoFileSystemManagement1Ptr_t me);

    /* IEcoFileSystemManagement1 */
    IEcoFileManager1* (ECOCALLMETHOD *get_FileManager)(/* in */ IEcoFileSystemManagement1Ptr_t me);
    IEcoDirectoryManager1* (ECOCALLMETHOD *get_DirectoryManager)(/* in */ IEcoFileSystemManagement1Ptr_t me);
    IEcoDriveManager1* (ECOCALLMETHOD *get_DriveManager)(/* in */ IEcoFileSystemManagement1Ptr_t me);

} IEcoFileSystemManagement1VTbl, *IEcoFileSystemManagement1VTblPtr;

interface IEcoFileSystemManagement1 {
    struct IEcoFileSystemManagement1VTbl *pVTbl;
} IEcoFileSystemManagement1;

#endif /* __I_ECO_FILE_SYSTEM_MANAGEMENT_1_H__ */
