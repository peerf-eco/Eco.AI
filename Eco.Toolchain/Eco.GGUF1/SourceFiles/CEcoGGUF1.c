/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   CEcoGGUF1_B24682B2
 * </summary>
 *
 * <description>
 *   This source code describes the implementation of the interfaces for CEcoGGUF1_B24682B2
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
#include "CEcoGGUF1.h"

/*
 *
 * <summary>
 *   QueryInterface Function
 * </summary>
 *
 * <description>
 *   QueryInterface function for the IEcoGGUF1 interface
 * </description>
 *
 */
static int16_t ECOCALLMETHOD CEcoGGUF1_B24682B2_QueryInterface(/* in */ IEcoGGUF1Ptr_t me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    CEcoGGUF1_B24682B2* pCMe = (CEcoGGUF1_B24682B2*)me;

    /* Pointer Validation */
    if (me == 0 || ppv == 0) {
        return ERR_ECO_POINTER;
    }

    /* Validate and retrieve requested interface */
    if ( IsEqualUGUID(riid, &IID_IEcoGGUF1) ) {
        *ppv = &pCMe->m_pVTblIEcoGGUF1;
        pCMe->m_pVTblIEcoGGUF1->AddRef((IEcoGGUF1*)pCMe);
    }
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown) ) {
        *ppv = &pCMe->m_pVTblIEcoGGUF1;
        pCMe->m_pVTblIEcoGGUF1->AddRef((IEcoGGUF1*)pCMe);
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
 *   AddRef function for the IEcoGGUF1 interface
 * </description>
 *
 */
static uint32_t ECOCALLMETHOD CEcoGGUF1_B24682B2_AddRef(/* in */ IEcoGGUF1Ptr_t me) {
    CEcoGGUF1_B24682B2* pCMe = (CEcoGGUF1_B24682B2*)me;

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
 *   Release function for the IEcoGGUF1 interface
 * </description>
 *
 */
static uint32_t ECOCALLMETHOD CEcoGGUF1_B24682B2_Release(/* in */ IEcoGGUF1Ptr_t me) {
    CEcoGGUF1_B24682B2* pCMe = (CEcoGGUF1_B24682B2*)me;

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
static int16_t ECOCALLMETHOD CEcoGGUF1_B24682B2_MyFunction(/* in */ IEcoGGUF1Ptr_t me, /* in */ char_t* Name, /* out */ char_t** copyName) {
    CEcoGGUF1_B24682B2* pCMe = (CEcoGGUF1_B24682B2*)me;
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
static int16_t ECOCALLMETHOD initCEcoGGUF1_B24682B2(/*in*/ CEcoGGUF1_B24682B2Ptr_t me, /* in */ IEcoUnknownPtr_t pIUnkSystem) {
    CEcoGGUF1_B24682B2* pCMe = (CEcoGGUF1_B24682B2*)me;
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
static int16_t ECOCALLMETHOD createCEcoGGUF1_B24682B2(/* in */ CEcoGGUF1_B24682B2Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoUnknownPtr_t pIUnkOuter) {
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
static void ECOCALLMETHOD deleteCEcoGGUF1_B24682B2(/* in */ CEcoGGUF1_B24682B2Ptr_t pCMe) {
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

/* IEcoGGUF1 Virtual Table */
IEcoGGUF1VTbl g_xE000F49AE6F046F3B93052E45BB81629VTbl_B24682B2 = {
    CEcoGGUF1_B24682B2_QueryInterface,
    CEcoGGUF1_B24682B2_AddRef,
    CEcoGGUF1_B24682B2_Release,
    CEcoGGUF1_B24682B2_MyFunction
};



/* Object Instance */
CEcoGGUF1_B24682B2 g_xCEcoGGUF1_B24682B2 = {
    &g_xE000F49AE6F046F3B93052E45BB81629VTbl_B24682B2,
    initCEcoGGUF1_B24682B2,
    createCEcoGGUF1_B24682B2,
    deleteCEcoGGUF1_B24682B2,
    1, /* m_cRef */
    0, /* m_pISys */
    0, /* m_pISys */
    0  /* m_Name */
};
