/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IdEcoTimeC89
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IdEcoTimeC89
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

#ifndef __ID_ECO_TIME_C89_H__
#define __ID_ECO_TIME_C89_H__

#include "IEcoBase1.h"
#include "IEcoTimeC89.h"

/* EcoTimeC89 CID = {00000000-0000-0000-0000-0000544D4531} */
#ifndef __CID_EcoTimeC89
static const UGUID CID_EcoTimeC89 = {0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x54, 0x4D, 0x45, 0x31}};
#endif /* __CID_EcoTimeC89 */

/* Фабрика компонента для динамической и статической компановки */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_000000000000000000000000544D4531;
#endif

#endif /* __ID_ECO_TIME_C89_H__ */
