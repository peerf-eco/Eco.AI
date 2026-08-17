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

#ifndef __I_ECO_FILE_SYSTEM_MANAGEMENT_1_HPP__
#define __I_ECO_FILE_SYSTEM_MANAGEMENT_1_HPP__

#include "IEcoBase1.hpp"
#include "IEcoFileManager1.hpp"
#include "IEcoDirectoryManager1.hpp"
#include "IEcoDriveManager1.hpp"

/* IEcoFileSystemManagement1 IID = {00000000-0000-0000-0000-C00000000101} */
#ifndef __IID_IEcoFileSystemManagement1
static const UGUID IID_IEcoFileSystemManagement1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x01, 0x01} };
#endif /* __IID_IEcoFileSystemManagement1 */

interface IEcoFileSystemManagement1 : public IEcoUnknown {
public:
    /* IEcoFileSystemManagement1 */
    virtual IEcoFileManager1* ECOCALLMETHOD get_FileManager(/* in*/ void) = 0;
    virtual IEcoDirectoryManager1* ECOCALLMETHOD get_DirectoryManager(/* in*/ void) = 0;
    virtual IEcoDriveManager1* ECOCALLMETHOD get_DriveManager(/* in*/ void) = 0;

};

#endif /* __I_ECO_FILE_SYSTEM_MANAGEMENT_1_HPP__ */
