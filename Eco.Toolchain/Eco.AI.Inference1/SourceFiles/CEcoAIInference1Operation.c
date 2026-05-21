/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   CEcoAIInference1Operation_D82986D3
 * </summary>
 *
 * <description>
 *   This source code describes the implementation of the interfaces for CEcoAIInference1Operation_D82986D3
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
#include "CEcoAIInference1Operation.h"

/*
 *
 * <summary>
 *   QueryInterface Function
 * </summary>
 *
 * <description>
 *   QueryInterface function for the IEcoAIOperation1 interface
 * </description>
 *
 */
static int16_t ECOCALLMETHOD CEcoAIInference1Operation_D82986D3_QueryInterface(/* in */ IEcoAIOperation1Ptr_t me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    CEcoAIInference1Operation_D82986D3* pCMe = (CEcoAIInference1Operation_D82986D3*)me;

    /* Pointer Validation */
    if (me == 0 || ppv == 0) {
        return ERR_ECO_POINTER;
    }

    /* Validate and retrieve requested interface */
    if ( IsEqualUGUID(riid, &IID_IEcoAIOperation1) ) {
        *ppv = &pCMe->m_pVTblIOperation;
        pCMe->m_pVTblIOperation->AddRef((IEcoAIOperation1*)pCMe);
    }
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown) ) {
        *ppv = &pCMe->m_pVTblIOperation;
        pCMe->m_pVTblIOperation->AddRef((IEcoAIOperation1*)pCMe);
    }
    else {
        *ppv = 0;
        return ERR_ECO_NOINTERFACE;
    }
    return ERR_ECO_SUCCESES;
}

/*
 *
 * <summary>
 *   AddRef Function
 * </summary>
 *
 * <description>
 *   AddRef function for the IEcoAIOperation1 interface
 * </description>
 *
 */
static uint32_t ECOCALLMETHOD CEcoAIInference1Operation_D82986D3_AddRef(/* in */ IEcoAIOperation1Ptr_t me) {
    CEcoAIInference1Operation_D82986D3* pCMe = (CEcoAIInference1Operation_D82986D3*)me;

    /* Pointer Validation */
    if (me == 0 ) {
        return -1; /* ERR_ECO_POINTER */
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
 *   Release function for the IEcoAIOperation1 interface
 * </description>
 *
 */
static uint32_t ECOCALLMETHOD CEcoAIInference1Operation_D82986D3_Release(/* in */ IEcoAIOperation1Ptr_t me) {
    CEcoAIInference1Operation_D82986D3* pCMe = (CEcoAIInference1Operation_D82986D3*)me;

    /* Pointer Validation */
    if (me == 0 ) {
        return -1; /* ERR_ECO_POINTER */
    }

    /* Decrementing the component's reference count */
    --pCMe->m_cRef;
    /* If the count is zero, free the instance data */
    if ( pCMe->m_cRef == 0 ) {
        pCMe->Delete(pCMe);
        return 0;
    }
    return pCMe->m_cRef;
}

static int16_t ECOCALLMETHOD CEcoAIInference1Operation_D82986D3_Execute(IEcoAIOperation1Ptr_t me, struct IEcoList1* pInEdges, struct IEcoList1* pOutEdges) {
    CEcoAIInference1Operation_D82986D3* pCMe = (CEcoAIInference1Operation_D82986D3*)me;

    /* Pointer Validation */
    if (me == 0) {
        return ERR_ECO_POINTER;
    }

    return ERR_ECO_SUCCESES;
}

static int16_t ECOCALLMETHOD CEcoAIInference1Operation_D82986D3_GetAttribute(IEcoAIOperation1Ptr_t me, char_t* attrName, void* pValue) {
    CEcoAIInference1Operation_D82986D3* pCMe = (CEcoAIInference1Operation_D82986D3*)me;

    /* Pointer Validation */
    if (me == 0) {
        return ERR_ECO_POINTER;
    }

    return ERR_ECO_SUCCESES;
}

static int16_t ECOCALLMETHOD CEcoAIInference1Operation_D82986D3_SetAttribute(IEcoAIOperation1Ptr_t me, char_t* attrName, void* pValue) {
    CEcoAIInference1Operation_D82986D3* pCMe = (CEcoAIInference1Operation_D82986D3*)me;

    /* Pointer Validation */
    if (me == 0) {
        return ERR_ECO_POINTER;
    }

    return ERR_ECO_SUCCESES;
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
static int16_t ECOCALLMETHOD initCEcoAIInference1Operation_D82986D3(/*in*/ CEcoAIInference1Operation_D82986D3Ptr_t me, /* in */ IEcoUnknownPtr_t pIUnkSystem) {
    CEcoAIInference1Operation_D82986D3* pCMe = (CEcoAIInference1Operation_D82986D3*)me;
    IEcoInterfaceBus1* pIBus = 0;
    IEcoInterfaceBus1MemExt* pIMemExt = 0;
    int16_t result = ERR_ECO_POINTER;
    UGUID* rcid = (UGUID*)&CID_EcoMemoryManager1;	

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
static int16_t ECOCALLMETHOD createCEcoAIInference1Operation_D82986D3(/* in */ CEcoAIInference1Operation_D82986D3Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoUnknownPtr_t pIUnkOuter) {
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
 *   Instance freeing function
 * </description>
 *
 */
static void ECOCALLMETHOD deleteCEcoAIInference1Operation_D82986D3(/* in */ CEcoAIInference1Operation_D82986D3Ptr_t pCMe) {
    IEcoMemoryAllocator1* pIMem = 0;

    if (pCMe != 0 ) {
        pIMem = pCMe->m_pIMem;
        /* Freeing */
        if ( pCMe->m_Name != 0 ) {
            pIMem->pVTbl->Free(pIMem, pCMe->m_Name);
        }
        if ( pCMe->m_pISys != 0 ) {
            pCMe->m_pISys->pVTbl->Release(pCMe->m_pISys);
        }
        pIMem->pVTbl->Free(pIMem, pCMe);
        pIMem->pVTbl->Release(pIMem);
    }
}

/* IEcoAIOperation1 Virtual Table */
IEcoAIOperation1VTbl g_xBB46C0B69C9D4A63A1DF5A01E3CC4B0AVTbl_D82986D3 = {
    CEcoAIInference1Operation_D82986D3_QueryInterface,
    CEcoAIInference1Operation_D82986D3_AddRef,
    CEcoAIInference1Operation_D82986D3_Release,
    CEcoAIInference1Operation_D82986D3_Execute,
    CEcoAIInference1Operation_D82986D3_GetAttribute,
    CEcoAIInference1Operation_D82986D3_SetAttribute
};



/* Object Instance */
CEcoAIInference1Operation_D82986D3 g_xCEcoAIInference1Operation_D82986D3 = {
    &g_xBB46C0B69C9D4A63A1DF5A01E3CC4B0AVTbl_D82986D3,
    initCEcoAIInference1Operation_D82986D3,
    createCEcoAIInference1Operation_D82986D3,
    deleteCEcoAIInference1Operation_D82986D3,
    1, /* m_cRef */
    0, /* m_pISys */
    0, /* m_pISys */
    0  /* m_Name */
};
