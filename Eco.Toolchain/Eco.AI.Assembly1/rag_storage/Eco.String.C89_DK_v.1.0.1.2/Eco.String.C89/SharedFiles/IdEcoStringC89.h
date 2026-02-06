/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IdEcoStringC89
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IdEcoStringC89
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

#ifndef __ID_ECO_STRING_C89_H__
#define __ID_ECO_STRING_C89_H__

#include "IEcoBase1.h"
#include "IEcoStringC89.h"

/* EcoStringC89 CID = {00000000-0000-0000-0000-000073747231} */
#ifndef __CID_EcoStringC89
static const UGUID CID_EcoStringC89 = {0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x73, 0x74, 0x72, 0x31}};
#endif /* __CID_EcoStringC89 */

/* Фабрика компонента для динамической и статической компановки */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_00000000000000000000000073747231;
#endif

#endif /* __ID_ECO_STRING_C89_H__ */
