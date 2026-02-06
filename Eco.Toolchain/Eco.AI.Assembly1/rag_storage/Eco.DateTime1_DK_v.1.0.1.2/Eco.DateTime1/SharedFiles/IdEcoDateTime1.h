/*
 * <кодировка символов>
 *   Cyrillic (Windows) - Codepage 1251
 * </кодировка символов>
 *
 * <сводка>
 *   IdEcoDateTime1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IdEcoDateTime1
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

#ifndef __ID_ECO_DATETIME_1_H__
#define __ID_ECO_DATETIME_1_H__

#include "IEcoBase1.h"
#include "IEcoDateTime1.h"

/* EcoDateTime1 CID = {5B2BA17B-EA70-4527-BC70-8F88568FE115} */
#ifndef __CID_EcoDateTime1
static const UGUID CID_EcoDateTime1 = {0x01, 0x10, {0x5B, 0x2B, 0xA1, 0x7B, 0xEA, 0x70, 0x45, 0x27, 0xBC, 0x70, 0x8F, 0x88, 0x56, 0x8F, 0xE1, 0x15} };
#endif /* __CID_EcoDateTime1 */

/* Фабрика компонента для динамической и статической компановки */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_5B2BA17BEA704527BC708F88568FE115;
#endif

#endif /* __ID_ECO_DATETIME_1_H__ */
