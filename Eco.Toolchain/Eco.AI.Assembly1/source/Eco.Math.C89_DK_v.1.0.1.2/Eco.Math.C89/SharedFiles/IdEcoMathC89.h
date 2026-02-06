/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IdEcoMathC89
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IdEcoMathC89
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

#ifndef __ID_ECO_MATH_C89_H__
#define __ID_ECO_MATH_C89_H__

#include "IEcoBase1.h"
#include "IEcoMathC89.h"

/* EcoMathC89 CID = {61C988E2-1B70-4137-8C5B-DAFBB68A3FA0} */
#ifndef __CID_EcoMathC89
static const UGUID CID_EcoMathC89 = {0x01, 0x10, {0x61, 0xC9, 0x88, 0xE2, 0x1B, 0x70, 0x41, 0x37, 0x8C, 0x5B, 0xDA, 0xFB, 0xB6, 0x8A, 0x3F, 0xA0} };
#endif /* __CID_EcoMathC89 */

/* Фабрика компонента для динамической и статической компановки */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_61C988E21B7041378C5BDAFBB68A3FA0;
#endif

#endif /* __ID_ECO_MATH_C89_H__ */
