/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   IdEcoONNX1
 * </summary>
 *
 * <description>
 *   This header describes the interface IdEcoONNX1
 * </description>
 *
 * <reference>
 *
 * </reference>
 *
 * <author>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </author>
 *
 */

#ifndef __ID_ECOONNX1_H__
#define __ID_ECOONNX1_H__

#include "IEcoBase1.h"
#include "IEcoONNX1.h"

/* EcoONNX1 CID = {6CFEE780-7C74-4D9B-A4FF-A3F1E6599735} */
#ifndef __CID_EcoONNX1
static const UGUID CID_EcoONNX1 = {0x01, 0x10, {0x6C, 0xFE, 0xE7, 0x80, 0x7C, 0x74, 0x4D, 0x9B, 0xA4, 0xFF, 0xA3, 0xF1, 0xE6, 0x59, 0x97, 0x35}};
#endif /* __CID_EcoONNX1 */

/* Component factory for dynamic and static layout */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_6CFEE7807C744D9BA4FFA3F1E6599735;
#endif

#endif /* __ID_ECOONNX1_H__ */

