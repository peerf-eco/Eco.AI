/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IdEcoStdIOC89
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IdEcoStdIOC89
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

#ifndef __ID_ECO_STD_IO_C89_H__
#define __ID_ECO_STD_IO_C89_H__

#include "IEcoBase1.h"
#include "IEcoStdIOC89.h"

/* EcoStdIOC89 CID = {00000000-0000-0000-0000-000053494F31} */
#ifndef __CID_EcoStdIOC89
static const UGUID CID_EcoStdIOC89 = {0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x53, 0x49, 0x4F, 0x31}};
#endif /* __CID_EcoStdIOC89 */

/* Фабрика компонента для динамической и статической компановки */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_00000000000000000000000053494F31;
#endif

#endif /* __ID_ECO_STD_IO_C89_H__ */
