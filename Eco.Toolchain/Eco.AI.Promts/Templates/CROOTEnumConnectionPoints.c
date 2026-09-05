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

#include "IEcoSystem1.h"
#include "IEcoInterfaceBus1.h"
#include "IEcoInterfaceBus1MemExt.h"
#include "C[!output FIX_PROJECT_NAME]EnumConnectionPoints.h"

/*
 *
 * <summary>
 *   QueryInterface Function
 * </summary>
 *
 * <description>
 *
 * </description>
 *
 */
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints_QueryInterface(/* in */ IEcoEnumConnectionPointsPtr_t me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    if (IsEqualUGUID(riid, &IID_IEcoUnknown) || IsEqualUGUID(riid, &IID_IEcoEnumConnectionPoints)) {
        *ppv = me;
    }
    else {
        *ppv = 0;
        return -1;
    }
    me->pVTbl->AddRef(me);
    return 0;
}

/*
 *
 * <summary>
 *   AddRef Function
 * </summary>
 *
 * <description>
 *
 * </description>
 *
 */
static uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints_AddRef(/* in */ IEcoEnumConnectionPointsPtr_t me) {
    return 0;
}

/*
 *
 * <summary>
 *   Release Function
 * </summary>
 *
 * <description>
 *
 * </description>
 *
 */
static uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints_Release(/* in */ IEcoEnumConnectionPointsPtr_t me) {
    return 0;
}

/*
 *
 * <summary>
 *   Next Function
 * </summary>
 *
 * <description>
 *
 * </description>
 *
 */
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints_Next(/* in */ IEcoEnumConnectionPointsPtr_t me, /* in */ uint32_t cConnections, /* out */ struct IEcoConnectionPoint **ppCP, /* out */ uint32_t *pcFetched) {
    return -1;
}

/*
 *
 * <summary>
 *   Skip Function
 * </summary>
 *
 * <description>
 *
 * </description>
 *
 */
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints_Skip(/* in */ IEcoEnumConnectionPointsPtr_t me, /* in */ uint32_t cConnections) {
    return -1;
}

/*
 *
 * <summary>
 *   Reset Function
 * </summary>
 *
 * <description>
 *
 * </description>
 *
 */
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints_Reset(/* in */ IEcoEnumConnectionPointsPtr_t me) {
    return 0 ;
}

/*
 *
 * <summary>
 *   Clone Function
 * </summary>
 *
 * <description>
 *
 * </description>
 *
 */
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints_Clone(/* in */ IEcoEnumConnectionPointsPtr_t me, /* out */ struct IEcoEnumConnectionPoints **ppEnum) {
    return 0;
}


/*
 *
 * <summary>
 *   Init Function
 * </summary>
 *
 * <description>
 *   Instance initialization function
 * </description>
 *
 */
static int16_t ECOCALLMETHOD initC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPointsPtr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ struct IEcoConnectionPoint *pCP) {
    IEcoInterfaceBus1* pIBus = 0;
    IEcoInterfaceBus1MemExt* pIMemExt = 0;
    int16_t result = ERR_ECO_POINTER;
    UGUID* rcid = (UGUID*)&CID_EcoMemoryManager1;	

    /* Pointer Validation */
    if (pCMe == 0 ) {
        return result;
    }

    /* Storing the pointer to the system interface */
    pCMe->m_pISys = (IEcoSystem1*)pIUnkSystem;

    /* Getting the interface for working with the interface bus */
    result = pCMe->m_pISys->pVTbl->QueryInterface(pCMe->m_pISys, &IID_IEcoInterfaceBus1, (void **)&pIBus);

    /* Getting the component ID for working with memory */
    result = pIBus->pVTbl->QueryInterface(pIBus, &IID_IEcoInterfaceBus1MemExt, (void**)&pIMemExt);
    if (result == 0 && pIMemExt != 0) {
        rcid = (UGUID*)pIMemExt->pVTbl->get_Manager(pIMemExt);
        pIMemExt->pVTbl->Release(pIMemExt);
    }

    /* Getting the memory allocator interface */
    result = pIBus->pVTbl->QueryComponent(pIBus, rcid, 0, &IID_IEcoMemoryAllocator1, (void**) &pCMe->m_pIMem);
    /* Check */
    if (result != 0 || pCMe->m_pIMem == 0) {
        result = ERR_ECO_GET_MEMORY_ALLOCATOR;
    }
    
    pCMe->m_List = 0;
    result = pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoList1, 0,  &IID_IEcoList1, (void**)&pCMe->m_List);
    if (result != 0 || pCMe->m_List == 0) {
        pCMe->Delete(pCMe);
        return result;
    }

    pCMe->m_List->pVTbl->Add(pCMe->m_List, pCP);

    /* Freeing */
    pIBus->pVTbl->Release(pIBus);

    return result;
}

/*
 *
 * <summary>
 *   Create Function
 * </summary>
 *
 * <description>
 *   Instance creation function
 * </description>
 *
 */
static int16_t ECOCALLMETHOD createC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPointsPtr_t pCMe, /* in */ IEcoUnknown* pIUnkSystem) {
     int16_t result = ERR_ECO_POINTER;

    /* Pointer Validation */
    if (pCMe == 0) {
        return result; /* ERR_ECO_POINTER */
    }


    return ERR_ECO_SUCCESES;
}

/*
 *
 * <summary>
 *   Delete Function
 * </summary>
 *
 * <description>
 * 
 * </description>
 *
 */
static void ECOCALLMETHOD deleteC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPointsPtr_t pCMe) {
 
    if (pCMe != 0 ) {
        if (pCMe->m_List != 0) {
            pCMe->m_List->pVTbl->Clear(pCMe->m_List);
            pCMe->m_List->pVTbl->Release(pCMe->m_List);
        }

    }
}

/* Create Virtual Table IEcoEnumConnectionPointsVTbl */
IEcoEnumConnectionPointsVTbl g_x0000000400000000C000000000000046VTblECP[!output GUID_CID_NAMESPACE] = {
	C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints_QueryInterface,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints_AddRef,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints_Release,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints_Next,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints_Skip,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints_Reset,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints_Clone	
};

/* Object Instance */
C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints g_xC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints = {
    &g_x0000000400000000C000000000000046VTblECP[!output GUID_CID_NAMESPACE],
    initC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints,
    createC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints,
    deleteC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints,
    0, /* m_pList */
    0, /* m_pIMem */
    0 /* m_pISys */  
};
