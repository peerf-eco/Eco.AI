/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints
 * </summary>
 *
 * <description>
 *   This header describes the implementation of the C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints component
 * </description>
 *
 * <author>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </author>
 *
 */

#ifndef __C_[!output UPPER_PROJECT_NAME]_ENUM_CONNECTION_POINTS_H__
#define __C_[!output UPPER_PROJECT_NAME]_ENUM_CONNECTION_POINTS_H__

#include "IEcoSystem1.h"
#include "IEcoEnumConnectionPoints.h"
#include "IdEcoList1.h"
#include "IdEcoMemoryManager1.h"

typedef struct C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints* C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPointsPtr_t;

typedef struct C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints {

    IEcoEnumConnectionPointsVTbl* m_pVTblIECP;

    int16_t (ECOCALLMETHOD *Init)(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPointsPtr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ struct IEcoConnectionPoint *pCP);
    int16_t (ECOCALLMETHOD *Create)(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPointsPtr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem);
    void (ECOCALLMETHOD *Delete)(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPointsPtr_t pCMe);

    IEcoList1* m_List;
    IEcoMemoryAllocator1* m_pIMem;
    IEcoSystem1* m_pISys;

} C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints;

#endif /* __C_[!output UPPER_PROJECT_NAME]_ENUM_CONNECTION_POINTS_H__ */
