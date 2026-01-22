/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   IdEcoGGUF1
 * </summary>
 *
 * <description>
 *   This header describes the interface IdEcoGGUF1
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

#ifndef __ID_ECOGGUF1_H__
#define __ID_ECOGGUF1_H__

#include "IEcoBase1.h"
#include "IEcoGGUF1.h"

/* EcoGGUF1 CID = {C7ADC3D5-07DD-4913-B5C4-4103B24682B2} */
#ifndef __CID_EcoGGUF1
static const UGUID CID_EcoGGUF1 = {0x01, 0x10, {0xC7, 0xAD, 0xC3, 0xD5, 0x07, 0xDD, 0x49, 0x13, 0xB5, 0xC4, 0x41, 0x03, 0xB2, 0x46, 0x82, 0xB2}};
#endif /* __CID_EcoGGUF1 */

/* Component factory for dynamic and static layout */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_C7ADC3D507DD4913B5C44103B24682B2;
#endif

#endif /* __ID_ECOGGUF1_H__ */

