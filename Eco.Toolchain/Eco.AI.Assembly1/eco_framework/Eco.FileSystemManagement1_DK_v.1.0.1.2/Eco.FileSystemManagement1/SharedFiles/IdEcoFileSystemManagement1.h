/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IdEcoFileSystemManagement1
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

#ifndef __ID_ECO_FILE_SYSTEM_MANAGEMENT_1_H__
#define __ID_ECO_FILE_SYSTEM_MANAGEMENT_1_H__

#include "IEcoBase1.h"
#include "IEcoFileManager1.h"
#include "IEcoDirectoryManager1.h"
#include "IEcoDriveManager1.h"
#include "IEcoFileSystemManagement1.h"

/* EcoFileSystemManagement1 CID = {00000000-0000-0000-0000-000046534D31} */
#ifndef __CID_EcoFileSystemManagement1
static const UGUID CID_EcoFileSystemManagement1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46, 0x53, 0x4D, 0x31} };
#endif /* __CID_EcoFileSystemManagement1 */

/* Фабрика компонента для динамической и статической компановки */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_00000000000000000000000046534D31;
#endif

#endif /* __ID_ECO_FILE_SYSTEM_MANAGEMENT_1_H__ */
