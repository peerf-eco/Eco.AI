/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IdEcoThreadManager1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IdEcoThreadManager1
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

#ifndef __ID_ECO_THREAD_MANAGER_1_H__
#define __ID_ECO_THREAD_MANAGER_1_H__

#include "IEcoBase1.h"
#include "IEcoThreadManager1.h"

/* EcoThreadManager1 CID = {B7D8E10E-1D35-40CC-B1CA-96F766AF1936} */
#ifndef __CID_EcoThreadManager1
static const UGUID CID_EcoThreadManager1 = {0x01, 0x10, {0xB7, 0xD8, 0xE1, 0x0E, 0x1D, 0x35, 0x40, 0xCC, 0xB1, 0xCA, 0x96, 0xF7, 0x66, 0xAF, 0x19, 0x36}};
#endif /* __CID_EcoThreadManager1 */

/* Фабрика компонента для динамической и статической компановки */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_B7D8E10E1D3540CCB1CA96F766AF1936;
#endif

#endif /* __ID_ECO_THREAD_MANAGER_1_H__ */
