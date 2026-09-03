/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IdEcoString1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IdEcoString1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __ID_ECO_STRING_1_H__
#define __ID_ECO_STRING_1_H__

#include "IEcoBase1.h"
#include "IEcoString1.h"

/* EcoString1 CID = {84CC0A7D-BABD-44EE-BE74-9C9A8312D37E} */
#ifndef __CID_EcoString1
static const UGUID CID_EcoString1 = { 0x01, 0x10, {0x84, 0xcc, 0x0a, 0x7d, 0xba, 0xbd, 0x44, 0xee, 0xbe, 0x74, 0x9c, 0x9a, 0x83, 0x12, 0xd3, 0x7e} };
#endif /* __CID_EcoString1 */

/* Фабрика компонента для динамической и статической компановки */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_84CC0A7DBABD44EEBE749C9A8312D37E;
#endif

#endif /* __ID_ECO_STRING_1_H__ */
