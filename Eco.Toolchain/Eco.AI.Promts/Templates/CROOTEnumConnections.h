/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections
 * </summary>
 *
 * <description>
 *   This header describes the implementation of the C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections component
 * </description>
 *
 * <author>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </author>
 *
 */

#ifndef __C_[!output UPPER_PROJECT_NAME]_ENUM_CONNECTIONS_H__
#define __C_[!output UPPER_PROJECT_NAME]_ENUM_CONNECTIONS_H__

#include "IEcoEnumConnections.h"
#include "IdEcoList1.h"
#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"

typedef struct C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections* C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionsPtr_t;

typedef struct C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections {

    IEcoEnumConnectionsVTbl* m_pVTblIEC;

    int16_t (ECOCALLMETHOD *Init)(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionsPtr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoList1* pIList);
    int16_t (ECOCALLMETHOD *Create)(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionsPtr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem);
    void (ECOCALLMETHOD *Delete)(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionsPtr_t pCMe);

    uint32_t m_cRef;
    IEcoList1* m_pSinkList;
    uint32_t m_cIndex;
    IEcoMemoryAllocator1* m_pIMem;
    IEcoSystem1* m_pISys;

} C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections;

#endif /* __C_[!output UPPER_PROJECT_NAME]_ENUM_CONNECTIONS_H__ */
