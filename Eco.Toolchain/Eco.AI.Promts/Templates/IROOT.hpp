/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   I[!output FIX_PROJECT_NAME]
 * </summary>
 *
 * <description>
 *   This header describes the interface I[!output FIX_PROJECT_NAME]
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

#ifndef __I_[!output UPPER_PROJECT_NAME]_HPP__
#define __I_[!output UPPER_PROJECT_NAME]_HPP__

#include "IEcoBase1.hpp"

/* I[!output FIX_PROJECT_NAME] IID = [!output GUID_IID] */
#ifndef __IID_I[!output FIX_PROJECT_NAME]
static const UGUID IID_I[!output FIX_PROJECT_NAME] = [!output GUID_IID_FORMATED];
#endif /* __IID_I[!output FIX_PROJECT_NAME] */

interface I[!output FIX_PROJECT_NAME] : public IEcoUnknown {
public:
    /* I[!output FIX_PROJECT_NAME] */
    virtual int16_t ECOCALLMETHOD MyFunction(/* in */ char_t* Name, /* out */ char_t** CopyName) = 0;

};

[!if ADD_CONNECTION_POINTS]
/* I[!output FIX_PROJECT_NAME]Events IID = [!output GUID_BID] */
#ifndef __IID_I[!output FIX_PROJECT_NAME]Events
static const UGUID IID_I[!output FIX_PROJECT_NAME]Events = [!output GUID_BID_FORMATED];
#endif /* __IID_I[!output FIX_PROJECT_NAME]Events */

/* Reverse interface */
interface I[!output FIX_PROJECT_NAME]Events : public IEcoUnknown {
public:
    /* I[!output FIX_PROJECT_NAME]Events */
    virtual int16_t ECOCALLMETHOD OnMyCallback(/* in */ char_t* Name) = 0;

};

[!endif]

#endif /* __I_[!output UPPER_PROJECT_NAME]_HPP__ */

