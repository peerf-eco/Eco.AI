/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   CEcoHDF5_0AAAA5F0
 * </summary>
 *
 * <description>
 *   This source code describes the implementation of the interfaces for CEcoHDF5_0AAAA5F0
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
#include "CEcoHDF5.h"

/*
 *
 * <summary>
 *   QueryInterface Function
 * </summary>
 *
 * <description>
 *   QueryInterface function for the IEcoHDF5 interface
 * </description>
 *
 */
static int16_t ECOCALLMETHOD CEcoHDF5_0AAAA5F0_QueryInterface(/* in */ IEcoHDF5Ptr_t me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    CEcoHDF5_0AAAA5F0* pCMe = (CEcoHDF5_0AAAA5F0*)me;

    /* Pointer Validation */
    if (me == 0 || ppv == 0) {
        return ERR_ECO_POINTER;
    }

    /* Validate and retrieve requested interface */
    if ( IsEqualUGUID(riid, &IID_IEcoHDF5) ) {
        *ppv = &pCMe->m_pVTblIEcoHDF5;
        pCMe->m_pVTblIEcoHDF5->AddRef((IEcoHDF5*)pCMe);
    }
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown) ) {
        *ppv = &pCMe->m_pVTblIEcoHDF5;
        pCMe->m_pVTblIEcoHDF5->AddRef((IEcoHDF5*)pCMe);
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
 *   AddRef function for the IEcoHDF5 interface
 * </description>
 *
 */
static uint32_t ECOCALLMETHOD CEcoHDF5_0AAAA5F0_AddRef(/* in */ IEcoHDF5Ptr_t me) {
    CEcoHDF5_0AAAA5F0* pCMe = (CEcoHDF5_0AAAA5F0*)me;

    /* Pointer Validation */
    if (me == 0 ) {
        return -1; /* ERR_ECO_POINTER */
    }


    return atomicincrement_int32_t(&pCMe->m_cRef);
}

/*
 *
 * <summary>
 *   Release Function
 * </summary>
 *
 * <description>
 *   Release function for the IEcoHDF5 interface
 * </description>
 *
 */
static uint32_t ECOCALLMETHOD CEcoHDF5_0AAAA5F0_Release(/* in */ IEcoHDF5Ptr_t me) {
    CEcoHDF5_0AAAA5F0* pCMe = (CEcoHDF5_0AAAA5F0*)me;

    /* Pointer Validation */
    if (me == 0 ) {
        return -1; /* ERR_ECO_POINTER */
    }

    /* Decrementing the component's reference count */

    atomicdecrement_int32_t(&pCMe->m_cRef);
    /* If the count is zero, free the instance data */
    if ( pCMe->m_cRef == 0 ) {
        pCMe->Delete(pCMe);
        return 0;
    }
    return pCMe->m_cRef;
}

/*
 *
 * <summary>
 *   MyFunction Function
 * </summary>
 *
 * <description>
 *   Function
 * </description>
 *
 */
static int16_t ECOCALLMETHOD CEcoHDF5_0AAAA5F0_MyFunction(/* in */ IEcoHDF5Ptr_t me, /* in */ char_t* Name, /* out */ char_t** copyName) {
    CEcoHDF5_0AAAA5F0* pCMe = (CEcoHDF5_0AAAA5F0*)me;
    int16_t index = 0;

    /* Pointer Validation */
    if (me == 0 || Name == 0 || copyName == 0) {
        return ERR_ECO_POINTER;
    }

    /* Copying the string */
    while(Name[index] != 0) {
        index++;
    }
    pCMe->m_Name = (char_t*)pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, index + 1);
    index = 0;
    while(Name[index] != 0) {
        pCMe->m_Name[index] = Name[index];
        index++;
    }
    *copyName = pCMe->m_Name;

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
static int16_t ECOCALLMETHOD initCEcoHDF5_0AAAA5F0(/*in*/ CEcoHDF5_0AAAA5F0Ptr_t me, /* in */ IEcoUnknownPtr_t pIUnkSystem) {
    CEcoHDF5_0AAAA5F0* pCMe = (CEcoHDF5_0AAAA5F0*)me;
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
static int16_t ECOCALLMETHOD createCEcoHDF5_0AAAA5F0(/* in */ CEcoHDF5_0AAAA5F0Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoUnknownPtr_t pIUnkOuter) {
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
static void ECOCALLMETHOD deleteCEcoHDF5_0AAAA5F0(/* in */ CEcoHDF5_0AAAA5F0Ptr_t pCMe) {
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

/* IEcoHDF5 Virtual Table */
IEcoHDF5VTbl g_xBB451325C05044C1BCC2E929C4C9F6ABVTbl_0AAAA5F0 = {
    CEcoHDF5_0AAAA5F0_QueryInterface,
    CEcoHDF5_0AAAA5F0_AddRef,
    CEcoHDF5_0AAAA5F0_Release,
    CEcoHDF5_0AAAA5F0_MyFunction
};



/* Object Instance */
CEcoHDF5_0AAAA5F0 g_xCEcoHDF5_0AAAA5F0 = {
    &g_xBB451325C05044C1BCC2E929C4C9F6ABVTbl_0AAAA5F0,
    initCEcoHDF5_0AAAA5F0,
    createCEcoHDF5_0AAAA5F0,
    deleteCEcoHDF5_0AAAA5F0,
    1, /* m_cRef */
    0, /* m_pISys */
    0, /* m_pISys */
    0  /* m_Name */
};
