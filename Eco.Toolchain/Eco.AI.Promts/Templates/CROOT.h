/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]
 * </summary>
 *
 * <description>
 *   This header describes the implementation of the C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE] component
 * </description>
 *
 * <author>
 *   Copyright (c) 2018 [!output AUTHOR]. All rights reserved.
 * </author>
 *
 */

#ifndef __C_[!output UPPER_PROJECT_NAME]_H__
#define __C_[!output UPPER_PROJECT_NAME]_H__

#include "I[!output FIX_PROJECT_NAME].h"
#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"
[!if ADD_CONNECTION_POINTS]
#include "IEcoEnumConnections.h"
#include "IEcoConnectionPointContainer.h"
#include "C[!output FIX_PROJECT_NAME]ConnectionPoint.h"
[!endif]
[!if ADD_CONTAINMENT_OUTER]
/*#include "IEcoXXXX.h"*/
[!endif]

typedef struct C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]Ptr_t;

typedef struct C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE] {

    /* I[!output FIX_PROJECT_NAME] interface function table */
    I[!output FIX_PROJECT_NAME]VTbl* m_pVTblI[!output FIX_PROJECT_NAME];

[!if ADD_AGGREGATION_INNER]
    /* Nondelegating IEcoUnknown interface */
    IEcoUnknownVTbl* m_pVTblINondelegatingUnk;

[!endif]
[!if ADD_CONTAINMENT_OUTER]
    /* IEcoXXXX interface function table */
    IEcoXXXXVTbl* m_pVTblIXXXX;

[!endif]
[!if ADD_CONNECTION_POINTS]
    /* IEcoConnectionPointContainer interface function table */
    IEcoConnectionPointContainerVTbl* m_pVTblICPC;

    /* Helper functions for notifications */
    int16_t (*Fire_OnMyCallback)(/* in */ struct C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* me, /* in */ char_t* Name);

[!endif]

    /* Instance initialization */
    int16_t (ECOCALLMETHOD *Init)(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem);
    /* Instance creation */
    int16_t (ECOCALLMETHOD *Create)(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoUnknownPtr_t pIUnkOuter);
    /* Deletion */
    void (ECOCALLMETHOD *Delete)(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]Ptr_t pCMe);


    /* Reference counter */
    uint32_t m_cRef;

    /* Interface for memory operations */
    IEcoMemoryAllocator1* m_pIMem;

    /* System interface */
    IEcoSystem1* m_pISys;

[!if ADD_CONNECTION_POINTS]
    /* Connection point */
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint* m_pISinkCP;

[!endif]
[!if ADD_AGGREGATION_INNER]
    /* Delegating IEcoUnknown, points to the outer or nondelegating IEcoUnknown */
    IEcoUnknown* m_pIUnkOuter;

[!endif]
[!if ADD_AGGREGATION_OUTER]
    /* Pointer to the inner component's IEcoUnknown */
    IEcoUnknown* m_pIUnkInner;

[!endif]
[!if ADD_CONTAINMENT_OUTER]
    /* Pointer to the included component's IEcoXXXX interface */
    IEcoXXXX* m_pIXXXX;

[!endif]
    /* Instance data */
    char_t* m_Name;

} C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE];

#endif /* __C_[!output UPPER_PROJECT_NAME]_H__ */
