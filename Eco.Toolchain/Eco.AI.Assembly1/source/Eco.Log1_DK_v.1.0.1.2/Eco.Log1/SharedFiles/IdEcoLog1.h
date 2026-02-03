/*
 * <кодировка символов>
 *   Cyrillic (Windows) - Codepage 1251
 * </кодировка символов>
 *
 * <сводка>
 *   IdEcoLog1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IdEcoLog1
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

#ifndef __ID_ECO_LOG_1_H__
#define __ID_ECO_LOG_1_H__

#include "IEcoBase1.h"
#include "IEcoLog1.h"

/* EcoLog1 CID = {97322B67-65B7-4342-BBCE-38798A0B40B5} */
#ifndef __CID_EcoLog1
static const UGUID CID_EcoLog1 = {0x01, 0x10, {0x97, 0x32, 0x2B, 0x67, 0x65, 0xB7, 0x43, 0x42, 0xBB, 0xCE, 0x38, 0x79, 0x8A, 0x0B, 0x40, 0xB5} };
#endif /* __CID_EcoLog1 */

/* Фабрика компонента для динамической и статической компановки */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_97322B6765B74342BBCE38798A0B40B5;
#endif

#endif /* __ID_ECO_LOG_1_H__ */
