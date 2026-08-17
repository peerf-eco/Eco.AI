/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IdEcoLocaleC89
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IdEcoLocaleC89
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

#ifndef __ID_ECO_LOCALE_C89_HPP__
#define __ID_ECO_LOCALE_C89_HPP__

#include "IEcoBase1.hpp"
#include "IEcoLocaleC89.hpp"

/* EcoLocaleC89 CID = {00000000-0000-0000-0000-00004C4F4331} */
#ifndef __CID_EcoLocaleC89
static const UGUID CID_EcoLocaleC89 = {0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x4C, 0x4F, 0x43, 0x31}};
#endif /* __CID_EcoLocaleC89 */

/* Фабрика компонента для динамической и статической компановки */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern "C" IEcoComponentFactory* GetIEcoComponentFactoryPtr_0000000000000000000000004C4F4331;
#endif

#endif /* __ID_ECO_LOCALE_C89_HPP__ */
