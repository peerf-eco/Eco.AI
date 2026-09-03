/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IdEcoSocketP02
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IdEcoSocketP02
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

#ifndef __ID_ECO_SOCKET_POSIX_2002_H__
#define __ID_ECO_SOCKET_POSIX_2002_H__

#include "IEcoBase1.h"
#include "IEcoSocketP02.h"

/* EcoSocketP02 CID = {1CE95396-008F-46EA-B437-4010C8B58383} */
#ifndef __CID_EcoSocketP02
static const UGUID CID_EcoSocketP02 = {0x01, 0x10, {0x1C, 0xE9, 0x53, 0x96, 0x00, 0x8F, 0x46, 0xEA, 0xB4, 0x37, 0x40, 0x10, 0xC8, 0xB5, 0x83, 0x83}};
#endif /* __CID_EcoSocketP02 */

/* Фабрика компонента для динамической и статической компановки */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_1CE95396008F46EAB4374010C8B58383;
#endif

#endif /* __ID_ECO_SOCKET_POSIX_2002_H__ */
