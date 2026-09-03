/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IdEcoSignalC89
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IdEcoSignalC89
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

#ifndef __ID_ECO_SIGNAL_C89_H__
#define __ID_ECO_SIGNAL_C89_H__

#include "IEcoBase1.h"
#include "IEcoSignalC89.h"

/* EcoSignalC89 CID = {00000000-0000-0000-0000-000053474C31} */
#ifndef __CID_EcoSignalC89
static const UGUID CID_EcoSignalC89 = {0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x53, 0x47, 0x4C, 0x31}};
#endif /* __CID_EcoSignalC89 */

/* Фабрика компонента для динамической и статической компановки */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_00000000000000000000000053474C31;
#endif

#endif /* __ID_ECO_SIGNAL_C89_H__ */
