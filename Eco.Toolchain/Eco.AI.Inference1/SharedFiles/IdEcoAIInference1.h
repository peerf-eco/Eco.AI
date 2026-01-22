/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   IdEcoAIInference1
 * </summary>
 *
 * <description>
 *   This header describes the interface IdEcoAIInference1
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

#ifndef __ID_ECOAIINFERENCE1_H__
#define __ID_ECOAIINFERENCE1_H__

#include "IEcoBase1.h"
#include "IEcoAIInference1.h"

/* EcoAIInference1 CID = {C5519906-D88D-49E9-BC8A-E817D82986D3} */
#ifndef __CID_EcoAIInference1
static const UGUID CID_EcoAIInference1 = {0x01, 0x10, {0xC5, 0x51, 0x99, 0x06, 0xD8, 0x8D, 0x49, 0xE9, 0xBC, 0x8A, 0xE8, 0x17, 0xD8, 0x29, 0x86, 0xD3}};
#endif /* __CID_EcoAIInference1 */

/* Component factory for dynamic and static layout */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_C5519906D88D49E9BC8AE817D82986D3;
#endif

#endif /* __ID_ECOAIINFERENCE1_H__ */

