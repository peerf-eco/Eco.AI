/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IdEcoMutex1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IdEcoMutex1
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

#ifndef __ID_ECO_MUTEX_1_H__
#define __ID_ECO_MUTEX_1_H__

#include "IEcoBase1.h"
#include "IEcoMutex1.h"

/* EcoMutex1 CID = {427A8D37-D291-4DCE-9710-D81099D5F190} */
#ifndef __CID_EcoMutex1
static const UGUID CID_EcoMutex1 = {0x01, 0x10, {0x42, 0x7A, 0x8D, 0x37, 0xD2, 0x91, 0x4D, 0xCE, 0x97, 0x10, 0xD8, 0x10, 0x99, 0xD5, 0xF1, 0x90} };
#endif /* __CID_EcoMutex1 */

/* Фабрика компонента для динамической и статической компановки */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_427A8D37D2914DCE9710D81099D5F190;
#endif

#endif /* __ID_ECO_MUTEX_1_H__ */
