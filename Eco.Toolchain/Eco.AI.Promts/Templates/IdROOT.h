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

#ifndef __ID_[!output UPPER_PROJECT_NAME]_H__
#define __ID_[!output UPPER_PROJECT_NAME]_H__

#include "IEcoBase1.h"
#include "I[!output FIX_PROJECT_NAME].h"

/* [!output FIX_PROJECT_NAME] CID = [!output GUID_CID] */
#ifndef __CID_[!output FIX_PROJECT_NAME]
static const UGUID CID_[!output FIX_PROJECT_NAME] = [!output GUID_CID_FORMATED];
#endif /* __CID_[!output FIX_PROJECT_NAME] */

/* Component factory for dynamic and static layout */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_[!output GUID_CID_TARGET];
#endif

#endif /* __ID_[!output UPPER_PROJECT_NAME]_H__ */

