/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IdEcoMemoryManager1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IdEcoMemoryManager1
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

#ifndef __ID_ECO_MEMORY_MANAGER_1_H__
#define __ID_ECO_MEMORY_MANAGER_1_H__

#include "IEcoBase1.h"
#include "IEcoMemoryManager1.h"

/* EcoMemoryManager1 CID = {00000000-0000-0000-0000-00004D656D31} */
#ifndef __CID_EcoMemoryManager1
static const UGUID CID_EcoMemoryManager1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x4D, 0x65, 0x6D, 0x31} };
#endif /* __CID_EcoMemoryManager1 */

/* Фабрика компонента для динамической и статической компановки */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr(void);
#elif ECO_LIB
extern struct IEcoComponentFactory* GetIEcoComponentFactoryPtr_0000000000000000000000004D656D31;
#endif

#endif /* __ID_ECO_MEMORY_MANAGER_1_H__ */

