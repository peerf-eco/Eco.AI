/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   C[!output FIX_PROJECT_NAME]ConnectionPoint
 * </сводка>
 *
 * <описание>
 *   Данный исходный код описывает реализацию интерфейсов C[!output FIX_PROJECT_NAME]ConnectionPoint
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#include "IEcoInterfaceBus1.h"
#include "IEcoInterfaceBus1MemExt.h"
#include "C[!output FIX_PROJECT_NAME]ConnectionPoint.h"
#include "C[!output FIX_PROJECT_NAME]EnumConnections.h"

extern C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections g_xC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections;

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
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint_QueryInterface(/* in */ struct IEcoConnectionPoint* me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint*)me;

    if (me == 0 || ppv == 0) {
        return -1;
    }

    if ( IsEqualUGUID(riid, &IID_IEcoConnectionPoint) ) {
        *ppv = &pCMe->m_pVTblICP;
        pCMe->m_pVTblICP->AddRef((IEcoConnectionPoint*)pCMe);
    }
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown) ) {
        *ppv = &pCMe->m_pVTblICP;
        pCMe->m_pVTblICP->AddRef((IEcoConnectionPoint*)pCMe);
    }
    else {
        *ppv = 0;
        return -1;
    }

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
static uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint_AddRef(/* in */ struct IEcoConnectionPoint* me) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint*)me;

    if (me == 0 ) {
        return -1;
    }

    return pCMe->m_pICPC->pVTbl->AddRef(pCMe->m_pICPC);
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
static uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint_Release(/* in */ struct IEcoConnectionPoint* me) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint*)me;

    if (me == 0 ) {
        return -1;
    }

    return pCMe->m_pICPC->pVTbl->Release(pCMe->m_pICPC);
}

/*
 *
 * <summary>
 *   GetConnectionInterface Function
 * </summary>
 *
 * <description>
 *
 * </description>
 *
 */
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint_GetConnectionInterface(/* in */ struct IEcoConnectionPoint* me, /* out */ UGUID *pIID) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint*)me;

    if (me == 0 || pIID == 0) {
        return -1;
    }

    pIID = (UGUID *)&pCMe->m_piid;
    return 0;
}

/*
 *
 * <summary>
 *   GetConnectionPointContainer Function
 * </summary>
 *
 * <description>
 *
 * </description>
 *
 */
 static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint_GetConnectionPointContainer(/* in */ struct IEcoConnectionPoint* me, /* out */ struct IEcoConnectionPointContainer **ppICPC) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint*)me;

    if (me == 0 || ppICPC == 0) {
        return -1;
    }

    *ppICPC = pCMe->m_pICPC;
    pCMe->m_pICPC->pVTbl->AddRef(pCMe->m_pICPC);

    return 0;
}

/*
 *
 * <summary>
 *   Advise Function
 * </summary>
 *
 * <description>
 *
 * </description>
 *
 */
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint_Advise(/* in */ struct IEcoConnectionPoint* me, /* in */ struct IEcoUnknown *pUnkSink, /* out */ uint32_t *pcCookie) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint*)me;
    int16_t result = 0;
    EcoConnectionData* pCD = 0;

    if (me == 0 || pUnkSink == 0 || pcCookie == 0) {
        return -1;
    }

    pCD = (EcoConnectionData*)pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, sizeof(EcoConnectionData));

    result = pUnkSink->pVTbl->QueryInterface(pUnkSink, pCMe->m_piid, (void**)&pCD->pUnk);
    if (result == 0 && pCD->pUnk != 0) {
        pCD->cCookie = ++pCMe->m_cNextCookie;
        pCMe->m_pSinkList->pVTbl->Add(pCMe->m_pSinkList, pCD);
        *pcCookie = pCD->cCookie;
        return 0;
    }

    return -1;
}

/*
 *
 * <summary>
 *   Unadvise Function
 * </summary>
 *
 * <description>
 *
 * </description>
 *
 */
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint_Unadvise(/* in */ struct IEcoConnectionPoint* me, /* in */ uint32_t cCookie) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint*)me;
    EcoConnectionData* pCD = 0;
    IEcoUnknown* pSink = 0;
    uint32_t indx = 0;
    uint32_t count = 0;

    if (me == 0 ) {
        return -1;
    }

    count = pCMe->m_pSinkList->pVTbl->Count(pCMe->m_pSinkList);
    for (indx = 0; indx < count; indx++) {
        pCD = (EcoConnectionData*)pCMe->m_pSinkList->pVTbl->Item(pCMe->m_pSinkList, indx);
        if (pCD->cCookie == cCookie) {
            pSink = pCD->pUnk;
            pCMe->m_pSinkList->pVTbl->RemoveAt(pCMe->m_pSinkList, indx);
            pSink->pVTbl->Release(pSink);
            pCMe->m_pIMem->pVTbl->Free(pCMe->m_pIMem, pCD);
            return 0;
        }
    }
    return -1;
}

/*
 *
 * <summary>
 *   EnumConnections Function
 * </summary>
 *
 * <description>
 *
 * </description>
 *
 */
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint_EnumConnections(/* in */ struct IEcoConnectionPoint* me, /* out */ struct IEcoEnumConnections **ppEnum) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint*)me;
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections* pCObj = 0;
    int16_t result = ERR_ECO_POINTER;

    if (me == 0 || ppEnum ==0 ) {
        return result;
    }

    pCObj = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections*)pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, sizeof(C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections));
    pCObj = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections*)pCMe->m_pIMem->pVTbl->Copy(pCMe->m_pIMem, pCObj, &g_xC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections, sizeof(C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnections));
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
static int16_t ECOCALLMETHOD initC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPointPtr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoConnectionPointContainer* pICPC, /* in */ const UGUID* riid) {
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
    
    pCMe->m_pICPC = pICPC;
    pCMe->m_piid = (UGUID*)riid;
	
    pCMe->m_pSinkList = 0;
    result = pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoList1, 0, &IID_IEcoList1, (void**)&pCMe->m_pSinkList);
    if (result != 0 || pCMe->m_pSinkList == 0) {
        pCMe->Delete(pCMe);
        return result;
    }

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
static int16_t ECOCALLMETHOD createC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPointPtr_t pCMe, /* in */ IEcoUnknown* pIUnkSystem) {
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
static void ECOCALLMETHOD deleteC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint(/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPointPtr_t pCMe) {
    EcoConnectionData* pCD = 0;
    uint32_t count = 0;
    uint32_t index = 0;

    if (pCMe != 0 ) {
        if (pCMe->m_pSinkList != 0) {
            count = pCMe->m_pSinkList->pVTbl->Count(pCMe->m_pSinkList);
            for (index = 0; index < count; index++) {
                pCD = (EcoConnectionData*)pCMe->m_pSinkList->pVTbl->Item(pCMe->m_pSinkList, index);
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

/* Create Virtual Table IEcoConnectionPointVTbl */
IEcoConnectionPointVTbl g_x0000000300000000C000000000000046VTblCP[!output GUID_CID_NAMESPACE] = {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint_QueryInterface,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint_AddRef,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint_Release,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint_GetConnectionInterface,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint_GetConnectionPointContainer,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint_Advise,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint_Unadvise,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint_EnumConnections
};

/* Object Instance */
C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint g_xC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint = {
    &g_x0000000300000000C000000000000046VTblCP[!output GUID_CID_NAMESPACE],
    initC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint,
    createC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint,
    deleteC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint,
    0, /* m_pICPC */
    0, /* m_piid */
    0, /* m_cNextCookie */
    0, /* m_pSinkList */
    0, /* m_pIMem */  
    0  /* m_pISys */
};
