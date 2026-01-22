/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   IdEcoHDF5
 * </summary>
 *
 * <description>
 *   This header describes the interface IdEcoHDF5
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

#ifndef __ID_ECOHDF5_H__
#define __ID_ECOHDF5_H__

#include "IEcoBase1.h"
#include "IEcoHDF5.h"

/* EcoHDF5 CID = {376B7D27-767B-4CDF-9A3F-7CAB0AAAA5F0} */
#ifndef __CID_EcoHDF5
static const UGUID CID_EcoHDF5 = {0x01, 0x10, {0x37, 0x6B, 0x7D, 0x27, 0x76, 0x7B, 0x4C, 0xDF, 0x9A, 0x3F, 0x7C, 0xAB, 0x0A, 0xAA, 0xA5, 0xF0}};
#endif /* __CID_EcoHDF5 */

/* Component factory for dynamic and static layout */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_376B7D27767B4CDF9A3F7CAB0AAAA5F0;
#endif

#endif /* __ID_ECOHDF5_H__ */

