/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint
 * </summary>
 *
 * <description>
 *   This header describes the implementation of the C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint component
 * </description>
 *
 * <author>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </author>
 *
 */

#ifndef __C_[!output UPPER_PROJECT_NAME]_CONNECTION_POINT_H__
#define __C_[!output UPPER_PROJECT_NAME]_CONNECTION_POINT_H__

#include "IEcoConnectionPoint.h"
#include "IEcoConnectionPointContainer.h"
#include "IdEcoList1.h"
#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"

typedef struct C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint* C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPointPtr_t;

typedef struct C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint {

    IEcoConnectionPointVTbl* m_pVTblICP;


    int16_t (ECOCALLMETHOD *Init)(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPointPtr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoConnectionPointContainer* pICPC, /* in */ const UGUID* riid);
    int16_t (ECOCALLMETHOD *Create)(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPointPtr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem);
    void (ECOCALLMETHOD *Delete)(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPointPtr_t pCMe);

    IEcoConnectionPointContainer* m_pICPC;
    UGUID* m_piid;
    uint32_t m_cNextCookie;
    IEcoList1* m_pSinkList;
    IEcoMemoryAllocator1* m_pIMem;
    IEcoSystem1* m_pISys;

} C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint;

#endif /* __C_[!output UPPER_PROJECT_NAME]_CONNECTION_POINT_H__ */
