/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IdEcoMathFFT1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IdEcoMathFFT1
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

#ifndef __ID_ECO_MATH_FFT_1_H__
#define __ID_ECO_MATH_FFT_1_H__

#include "IEcoBase1.h"
#include "IEcoMathFFT1.h"

/* EcoMathFFT1 CID = {99A58C53-14CC-4D0A-B006-2A865E3EA68D} */
#ifndef __CID_EcoMathFFT1
static const UGUID CID_EcoMathFFT1 = {0x01, 0x10, {0x99, 0xA5, 0x8C, 0x53, 0x14, 0xCC, 0x4D, 0x0A, 0xB0, 0x06, 0x2A, 0x86, 0x5E, 0x3E, 0xA6, 0x8D} };
#endif /* __CID_EcoMathFFT1 */

/* Фабрика компонента для динамической и статической компановки */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_99A58C5314CC4D0AB0062A865E3EA68D;
#endif

#endif /* __ID_ECO_MATH_FFT_1_H__ */
