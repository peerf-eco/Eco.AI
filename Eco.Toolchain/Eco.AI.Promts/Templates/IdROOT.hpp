/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   Id[!output FIX_PROJECT_NAME]
 * </summary>
 *
 * <description>
 *   This header describes the interface Id[!output FIX_PROJECT_NAME]
 * </description>
 *
 * <reference>
 *
 * </reference>
 *
 * <author>
 *   Copyright (c) 2026 [!output AUTHOR]. All rights reserved.
 * </author>
 *
 */

#ifndef __ID_[!output UPPER_PROJECT_NAME]_HPP__
#define __ID_[!output UPPER_PROJECT_NAME]_HPP__

#include "IEcoBase1.hpp"
#include "I[!output FIX_PROJECT_NAME].hpp"

/* [!output FIX_PROJECT_NAME] CID = [!output GUID_CID] */
#ifndef __CID_[!output FIX_PROJECT_NAME]
static const UGUID CID_[!output FIX_PROJECT_NAME] = [!output GUID_CID_FORMATED];
#endif /* __CID_[!output FIX_PROJECT_NAME] */

/* Component factory for dynamic and static layout */
#ifdef ECO_DLL
extern "C" ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern "C" IEcoComponentFactory* GetIEcoComponentFactoryPtr_[!output GUID_CID_TARGET];
#endif

#endif /* __ID_[!output UPPER_PROJECT_NAME]_HPP__ */

