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

#ifndef __I_[!output UPPER_PROJECT_NAME]_H__
#define __I_[!output UPPER_PROJECT_NAME]_H__

#include "IEcoBase1.h"

/* I[!output FIX_PROJECT_NAME] IID = [!output GUID_IID] */
#ifndef __IID_I[!output FIX_PROJECT_NAME]
static const UGUID IID_I[!output FIX_PROJECT_NAME] = [!output GUID_IID_FORMATED];
#endif /* __IID_I[!output FIX_PROJECT_NAME] */

typedef struct I[!output FIX_PROJECT_NAME]* I[!output FIX_PROJECT_NAME]Ptr_t;

typedef struct I[!output FIX_PROJECT_NAME]VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ I[!output FIX_PROJECT_NAME]Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ I[!output FIX_PROJECT_NAME]Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ I[!output FIX_PROJECT_NAME]Ptr_t me);

    /* I[!output FIX_PROJECT_NAME] */
    int16_t (ECOCALLMETHOD *MyFunction)(/* in */ I[!output FIX_PROJECT_NAME]Ptr_t me, /* in */ char_t* Name, /* out */ char_t** CopyName);

} I[!output FIX_PROJECT_NAME]VTbl, *I[!output FIX_PROJECT_NAME]VTblPtr_t;

interface I[!output FIX_PROJECT_NAME] {
    struct I[!output FIX_PROJECT_NAME]VTbl *pVTbl;
} I[!output FIX_PROJECT_NAME];

[!if ADD_CONNECTION_POINTS]
/* I[!output FIX_PROJECT_NAME]Events IID = [!output GUID_BID] */
#ifndef __IID_I[!output FIX_PROJECT_NAME]Events
static const UGUID IID_I[!output FIX_PROJECT_NAME]Events = [!output GUID_BID_FORMATED];
#endif /* __IID_I[!output FIX_PROJECT_NAME]Events */

typedef struct I[!output FIX_PROJECT_NAME]Events* I[!output FIX_PROJECT_NAME]EventsPtr_t;

/* Reverse interface */
typedef struct I[!output FIX_PROJECT_NAME]VTblEvents {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface )(/* in */ I[!output FIX_PROJECT_NAME]EventsPtr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef )(/* in */ I[!output FIX_PROJECT_NAME]EventsPtr_t me);
    uint32_t (ECOCALLMETHOD *Release )(/* in */ I[!output FIX_PROJECT_NAME]EventsPtr_t me);

    /* I[!output FIX_PROJECT_NAME]Events */
    int16_t (ECOCALLMETHOD *OnMyCallback)(/* in */ I[!output FIX_PROJECT_NAME]EventsPtr_t me, /* in */ char_t* Name);

} I[!output FIX_PROJECT_NAME]VTblEvents, *I[!output FIX_PROJECT_NAME]VTblEventsPtr_t;

interface I[!output FIX_PROJECT_NAME]Events {
    struct I[!output FIX_PROJECT_NAME]VTblEvents *pVTbl;
} I[!output FIX_PROJECT_NAME]Events;

[!endif]

#endif /* __I_[!output UPPER_PROJECT_NAME]_H__ */

