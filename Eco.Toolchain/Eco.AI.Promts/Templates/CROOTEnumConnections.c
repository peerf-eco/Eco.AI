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
#include "IEcoInterfaceBus1.h"
#include "IEcoInterfaceBus1MemExt.h"
#include "C[!output FIX_PROJECT_NAME]EnumConnections.h"

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
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections_QueryInterface(/* in */ IEcoEnumConnectionsPtr_t me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    if (IsEqualUGUID(riid, &IID_IEcoUnknown) || IsEqualUGUID(riid, &IID_IEcoEnumConnections)) {
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
static uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections_AddRef(/* in */ IEcoEnumConnectionsPtr_t me) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections*)me;

    if (me == 0 ) {
        return -1;
    }

    return ++pCMe->m_cRef;
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
static uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections_Release(/* in */ IEcoEnumConnectionsPtr_t me) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections*)me;

    if (me == 0 ) {
        return -1;
    }

    --pCMe->m_cRef;

    if ( pCMe->m_cRef == 0 ) {
        pCMe->Delete(pCMe);
        return 0;
    }
    return pCMe->m_cRef;
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
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections_Next(/* in */ IEcoEnumConnectionsPtr_t me, /* in */ uint32_t cConnections, /* out */ struct EcoConnectionData *rgcd, /* out */ uint32_t *pcFetched) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections*)me;
    EcoConnectionData* pCD = 0;
    uint32_t count = 0;

    if (me == 0 || rgcd == 0 || (pcFetched == 0 && cConnections > 1) ) {
        return -1;
    }

    while ((pCMe->m_cIndex < pCMe->m_pSinkList->pVTbl->Count(pCMe->m_pSinkList)) && (count < cConnections)) {
        pCD = (EcoConnectionData*)pCMe->m_pSinkList->pVTbl->Item(pCMe->m_pSinkList, pCMe->m_cIndex);
        pCD->pUnk->pVTbl->AddRef(pCD->pUnk);
        rgcd->pUnk = pCD->pUnk;
        rgcd->cCookie = pCD->cCookie;
        count++;
        pCMe->m_cIndex++;
    };

    if (pcFetched != 0) {
        *pcFetched = count;
    }

    if (count < cConnections) {
        return -1;
    }
    else {
        return 0;
    }

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
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections_Skip(/* in */ IEcoEnumConnectionsPtr_t me, /* in */ uint32_t cConnections) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections*)me;
    uint32_t count = 0;

    if (me == 0 ) {
        return -1;
    }

    while ((pCMe->m_cIndex < pCMe->m_pSinkList->pVTbl->Count(pCMe->m_pSinkList)) && (count < cConnections)) {
        count++;
        pCMe->m_cIndex++;
    };

    if (count < cConnections) {
        return -1;
    }
    else {
        return 0;
    }

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
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections_Reset(/* in */ IEcoEnumConnectionsPtr_t me) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections*)me;

    if (me == 0 ) {
        return -1;
    }

    pCMe->m_cIndex = 0;

    return 0;
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
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections_Clone(/* in */ IEcoEnumConnectionsPtr_t me, /* out */ struct IEcoEnumConnections **ppEnum) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections*)me;
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections* pCObj = 0;
    int16_t result = ERR_ECO_POINTER;

    if (me == 0 || ppEnum ==0 ) {
        return result;
    }

    pCObj = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections*)pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, sizeof(C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections));
    pCObj = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections*)pCMe->m_pIMem->pVTbl->Copy(pCMe->m_pIMem, pCObj, pCMe, sizeof(C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections));
    pCObj->Create(pCObj, (IEcoUnknownPtr_t)pCMe->m_pISys);
    result = pCObj->Init(pCObj, (IEcoUnknownPtr_t)pCMe->m_pISys, pCMe->m_pSinkList);
    *ppEnum = (IEcoEnumConnectionsPtr_t)pCObj;

    return result;
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
static int16_t ECOCALLMETHOD initC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionsPtr_t me, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoList1* pIList) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections*)me;
    IEcoInterfaceBus1* pIBus = 0;
    IEcoInterfaceBus1MemExt* pIMemExt = 0;
    int16_t result = ERR_ECO_POINTER;
    UGUID* rcid = (UGUID*)&CID_EcoMemoryManager1;	
    EcoConnectionData* pCD = 0;
    EcoConnectionData* pNewCD = 0;
    uint32_t indx = 0;

    /* Pointer Validation */
    if (me == 0 ) {
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

    pCMe->m_pSinkList = 0;
    result = pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoList1, 0,  &IID_IEcoList1, (void**)&pCMe->m_pSinkList);
    if (result != 0 || pCMe->m_pSinkList == 0) {
        pCMe->Delete(pCMe);
        return result;
    }
    for (indx = 0; indx < pIList->pVTbl->Count(pIList); indx++) {
        pCD = (EcoConnectionData*)pIList->pVTbl->Item(pIList, indx);
        pNewCD = (EcoConnectionData*)pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, sizeof(EcoConnectionData));
        pNewCD->cCookie = pCD->cCookie;
        pNewCD->pUnk = pCD->pUnk;
        pNewCD->pUnk->pVTbl->AddRef(pNewCD->pUnk);
        pCMe->m_pSinkList->pVTbl->Add(pCMe->m_pSinkList, pNewCD);
    }
    pCMe->m_cIndex = 0;

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
static int16_t ECOCALLMETHOD createC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections(/* in */ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections* pCMe, /* in */ IEcoUnknown* pIUnkSystem) {
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
static void ECOCALLMETHOD deleteC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections(/* in */ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections* pCMe) {
    uint32_t indx = 0;
    EcoConnectionData* pCD = 0;

    if (pCMe != 0 ) {
        if (pCMe->m_pSinkList != 0) {
            for (indx = 0; indx < pCMe->m_pSinkList->pVTbl->Count(pCMe->m_pSinkList); indx++) {
                pCD = (EcoConnectionData*)pCMe->m_pSinkList->pVTbl->Item(pCMe->m_pSinkList, indx);
                pCD->pUnk->pVTbl->Release(pCD->pUnk);
                pCMe->m_pIMem->pVTbl->Free(pCMe->m_pIMem, pCD);
            }
            pCMe->m_pSinkList->pVTbl->Clear(pCMe->m_pSinkList);
            pCMe->m_pSinkList->pVTbl->Release(pCMe->m_pSinkList);
        }
        if (pCMe->m_pISys != 0) {
            pCMe->m_pISys->pVTbl->Release(pCMe->m_pISys);
            pCMe->m_pISys = 0;
        }
    }
}

/* Create Virtual Table IEcoEnumConnectionsVTbl */
IEcoEnumConnectionsVTbl g_x0000000200000000C000000000000046VTblECP[!output GUID_CID_NAMESPACE] = {
	C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections_QueryInterface,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections_AddRef,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections_Release,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections_Next,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections_Skip,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections_Reset,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections_Clone	
};

/* Object Instance */
C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections g_xC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections = {
    &g_x0000000200000000C000000000000046VTblECP[!output GUID_CID_NAMESPACE],
    initC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections,
    createC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections,
    deleteC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections,
    1, /* m_cRef */
    0, /* m_pSinkList */
    0, /* m_cIndex */
    0, /* m_pIMem */  
    0  /* m_pISys */
};
