/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   IdEcoAIEngine1
 * </summary>
 *
 * <description>
 *   This header describes the interface IdEcoAIEngine1
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

#ifndef __ID_ECOAIENGINE1_H__
#define __ID_ECOAIENGINE1_H__

#include "IEcoBase1.h"
#include "IEcoAIEngine1.h"

/* EcoAIEngine1 CID = {6E5C5B7C-979F-4010-8F7C-DC08EADFB777} */
#ifndef __CID_EcoAIEngine1
static const UGUID CID_EcoAIEngine1 = {0x01, 0x10, {0x6E, 0x5C, 0x5B, 0x7C, 0x97, 0x9F, 0x40, 0x10, 0x8F, 0x7C, 0xDC, 0x08, 0xEA, 0xDF, 0xB7, 0x77}};
#endif /* __CID_EcoAIEngine1 */

/* Component factory for dynamic and static layout */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_6E5C5B7C979F40108F7CDC08EADFB777;
#endif

#endif /* __ID_ECOAIENGINE1_H__ */

