/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IdEcoInterfaceBus1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IdEcoInterfaceBus1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __ID_ECO_INTERFACE_BUS_1_H__
#define __ID_ECO_INTERFACE_BUS_1_H__

#include "IEcoBase1.h"
#include "IEcoInterfaceBus1.h"

/* EcoInterfaceBus1 CID = {00000000-0000-0000-0000-000042757331} */
#ifndef __CID_EcoInterfaceBus1
static const UGUID CID_EcoInterfaceBus1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x42, 0x75, 0x73, 0x31} };
#endif /* __CID_EcoInterfaceBus1 */

/* Фабрика компонента для динамической и статической компановки */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_00000000000000000000000042757331;
#endif

#endif /* __ID_ECO_INTERFACE_BUS_1_H__ */
