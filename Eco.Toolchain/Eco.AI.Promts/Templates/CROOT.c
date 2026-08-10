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
 *   This source code describes the implementation of the interfaces for C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]
 * </description>
 *
 * <author>
 *   Copyright (c) 2026 [!output AUTHOR]. All rights reserved.
 * </author>
 *
 */


#include "IEcoSystem1.h"
#include "IEcoInterfaceBus1.h"
#include "IEcoInterfaceBus1MemExt.h"
#include "C[!output FIX_PROJECT_NAME].h"
[!if ADD_CONNECTION_POINTS]
#include "C[!output FIX_PROJECT_NAME]EnumConnectionPoints.h"
#include "IEcoConnectionPointContainer.h"

extern C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints g_xC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints;
extern C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint g_xC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint;
[!endif]
/*
 *
 * <summary>
 *   QueryInterface Function
 * </summary>
 *
 * <description>
 *   QueryInterface function for the I[!output FIX_PROJECT_NAME] interface
 * </description>
 *
 */
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_QueryInterface(/* in */ I[!output FIX_PROJECT_NAME]Ptr_t me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)me;

    /* Pointer Validation */
    if (me == 0 || ppv == 0) {
        return ERR_ECO_POINTER;
    }

[!if ADD_AGGREGATION_INNER]
    return pCMe->m_pIUnkOuter->pVTbl->QueryInterface(pCMe->m_pIUnkOuter, riid, ppv);
[!else]
    /* Validate and retrieve requested interface */
    if ( IsEqualUGUID(riid, &IID_I[!output FIX_PROJECT_NAME]) ) {
        *ppv = &pCMe->m_pVTblI[!output FIX_PROJECT_NAME];
        pCMe->m_pVTblI[!output FIX_PROJECT_NAME]->AddRef((I[!output FIX_PROJECT_NAME]*)pCMe);
    }
[!if ADD_CONTAINMENT_OUTER]
    else if (IsEqualUGUID(riid, &IID_IEcoXXX)) {
        *ppv = &pCMe->m_pVTblIXXXX;
        pCMe->m_pVTblI[!output FIX_PROJECT_NAME]->AddRef((I[!output FIX_PROJECT_NAME]*)pCMe);
    }
[!endif]	
[!if ADD_CONNECTION_POINTS]
    else if ( IsEqualUGUID(riid, &IID_IEcoConnectionPointContainer) ) {
        *ppv = &pCMe->m_pVTblICPC;
        pCMe->m_pVTblICPC->AddRef((IEcoConnectionPointContainer*)pCMe);
    }
[!endif]
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown) ) {
        *ppv = &pCMe->m_pVTblI[!output FIX_PROJECT_NAME];
        pCMe->m_pVTblI[!output FIX_PROJECT_NAME]->AddRef((I[!output FIX_PROJECT_NAME]*)pCMe);
    }
[!if ADD_AGGREGATION_OUTER]
    /* Blind aggregation */
    else if (pCMe->m_pIUnkInner != 0) {
        /* Querying the inner component for an interface */
        return pCMe->m_pIUnkInner->pVTbl->QueryInterface(pCMe->m_pIUnkInner, riid, ppv);
    }
[!endif]
    else {
        *ppv = 0;
        return ERR_ECO_NOINTERFACE;
    }
    return ERR_ECO_SUCCESES;
[!endif]
}

/*
 *
 * <summary>
 *   AddRef Function
 * </summary>
 *
 * <description>
 *   AddRef function for the I[!output FIX_PROJECT_NAME] interface
 * </description>
 *
 */
static uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_AddRef(/* in */ I[!output FIX_PROJECT_NAME]Ptr_t me) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)me;

    /* Pointer Validation */
    if (me == 0 ) {
        return -1; /* ERR_ECO_POINTER */
    }

[!if ADD_AGGREGATION_INNER]
    return pCMe->m_pIUnkOuter->pVTbl->AddRef(pCMe->m_pIUnkOuter);
[!else]
[!if THREAD_SAFE]
    return atomicincrement_int32_t(&pCMe->m_cRef);
[!else]
    return ++pCMe->m_cRef;
[!endif]
[!endif]
}

/*
 *
 * <summary>
 *   Release Function
 * </summary>
 *
 * <description>
 *   Release function for the I[!output FIX_PROJECT_NAME] interface
 * </description>
 *
 */
static uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_Release(/* in */ I[!output FIX_PROJECT_NAME]Ptr_t me) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)me;

    /* Pointer Validation */
    if (me == 0 ) {
        return -1; /* ERR_ECO_POINTER */
    }

[!if ADD_AGGREGATION_INNER]
    return pCMe->m_pIUnkOuter->pVTbl->Release(pCMe->m_pIUnkOuter);
[!else]
    /* Decrementing the component's reference count */
[!if THREAD_SAFE]
    atomicdecrement_int32_t(&pCMe->m_cRef);
[!else]
    --pCMe->m_cRef;
[!endif]
    /* If the count is zero, free the instance data */
    if ( pCMe->m_cRef == 0 ) {
[!if ADD_AGGREGATION_OUTER]
        if ( pCMe->m_pIUnkInner != 0 ) {
            /* Preventing recursive calls */
            if (pCMe->m_pIUnkInner->pVTbl->Release(pCMe->m_pIUnkInner) == 0) {
                pCMe->m_pIUnkInner = 0;
            }
            else {
                pCMe->m_cRef = 1;
            }
        }
        if ( pCMe->m_cRef == 0 ) {
            pCMe->Delete(pCMe);
        }		
[!else]
        pCMe->Delete(pCMe);
[!endif]		
        return 0;
    }
    return pCMe->m_cRef;
[!endif]
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
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_MyFunction(/* in */ I[!output FIX_PROJECT_NAME]Ptr_t me, /* in */ char_t* Name, /* out */ char_t** copyName) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)me;
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

[!if ADD_CONNECTION_POINTS]
    /* Callback */
    pCMe->Fire_OnMyCallback(pCMe, pCMe->m_Name);

[!endif]
    return ERR_ECO_SUCCESES;
}

[!if ADD_AGGREGATION_INNER]
/*
 *
 * <summary>
 *   NondelegatingQueryInterface Function
 * </summary>
 *
 * <description>
 *   NondelegatingQueryInterface function for the I[!output FIX_PROJECT_NAME] interface
 * </description>
 *
 */
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_NondelegatingQueryInterface(/* in */ I[!output FIX_PROJECT_NAME]Ptr_t me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[!output FIX_PROJECT_NAME]*));

    /* Pointer Validation */
    if (me == 0 || ppv == 0) {
        return ERR_ECO_POINTER;
    }

    /* Validate and retrieve requested interface */
    if ( IsEqualUGUID(riid, &IID_I[!output FIX_PROJECT_NAME]) ) {
        *ppv = &pCMe->m_pVTblI[!output FIX_PROJECT_NAME];
        pCMe->m_pVTblI[!output FIX_PROJECT_NAME]->AddRef((I[!output FIX_PROJECT_NAME]*)pCMe);
    }
[!if ADD_CONNECTION_POINTS]
    else if ( IsEqualUGUID(riid, &IID_IEcoConnectionPointContainer) ) {
        *ppv = &pCMe->m_VtblICPC;
        pCMe->m_pVTblICPC->AddRef((IEcoConnectionPointContainer*)pCMe);
    }
[!endif]
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown) ) {
        *ppv = &pCMe->m_pVTblI[!output FIX_PROJECT_NAME];
        pCMe->m_pVTblI[!output FIX_PROJECT_NAME]->AddRef((I[!output FIX_PROJECT_NAME]*)pCMe);
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
 *   NondelegatingAddRef Function
 * </summary>
 *
 * <description>
 *   NondelegatingAddRef function for the I[!output FIX_PROJECT_NAME] interface
 * </description>
 *
 */
static uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_NondelegatingAddRef(/* in */ I[!output FIX_PROJECT_NAME]Ptr_t me) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[!output FIX_PROJECT_NAME]*));

    /* Pointer Validation */
    if (me == 0 ) {
        return -1; /* ERR_ECO_POINTER */
    }

[!if THREAD_SAFE]
    return atomicincrement_int32_t(&pCMe->m_cRef);
[!else]
    return ++pCMe->m_cRef;
[!endif]
}
/*
 *
 * <summary>
 *   NondelegatingRelease Function
 * </summary>
 *
 * <description>
 *   NondelegatingRelease function for the I[!output FIX_PROJECT_NAME] interface
 * </description>
 *
 */
static uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_NondelegatingRelease(/* in */ I[!output FIX_PROJECT_NAME]Ptr_t me) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[!output FIX_PROJECT_NAME]*));

    /* Pointer Validation */
    if (me == 0 ) {
        return -1; /* ERR_ECO_POINTER */
    }

    /* Decrementing the component's reference count */
[!if THREAD_SAFE]
    atomicdecrement_int32_t(&pCMe->m_cRef);
[!else]
    --pCMe->m_cRef;
[!endif]

    /* If the count is zero, free the instance data */
    if ( pCMe->m_cRef == 0 ) {
        pCMe->Delete(pCMe);
        return 0;
    }
    return pCMe->m_cRef;
}
[!endif]

[!if ADD_CONTAINMENT_OUTER]
/*
 *
 * <summary>
 *   QueryInterface Function
 * </summary>
 *
 * <description>
 *   QueryInterface function for the IEcoXXXX interface
 * </description>
 *
 */
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_IEcoXXXX_QueryInterface(/* in */ struct IEcoXXXX* me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[!output FIX_PROJECT_NAME]*));

    /* Pointer Validation */
    if (me == 0 || ppv == 0) {
        return ERR_ECO_POINTER;
    }

    /* Validate and retrieve requested interface */
    if ( IsEqualUGUID(riid, &IID_I[!output FIX_PROJECT_NAME]) ) {
        *ppv = &pCMe->m_pVTblI[!output FIX_PROJECT_NAME];
        pCMe->m_pVTblI[!output FIX_PROJECT_NAME]->AddRef((I[!output FIX_PROJECT_NAME]*)pCMe);
    }
    else if (IsEqualUGUID(riid, &IID_IEcoXXX)) {
        *ppv = &pCMe->m_pVTblIXXXX;
        pCMe->m_pVTblI[!output FIX_PROJECT_NAME]->AddRef((I[!output FIX_PROJECT_NAME]*)pCMe);
    }	
[!if ADD_CONNECTION_POINTS]
    else if ( IsEqualUGUID(riid, &IID_IEcoConnectionPointContainer) ) {
        *ppv = &pCMe->m_VtblICPC;
        pCMe->m_pVTblICPC->AddRef((IEcoConnectionPointContainer*)pCMe);
    }
[!endif]
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown) ) {
        *ppv = &pCMe->m_pVTblI[!output FIX_PROJECT_NAME];
        pCMe->m_pVTblI[!output FIX_PROJECT_NAME]->AddRef((I[!output FIX_PROJECT_NAME]*)pCMe);
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
 *   AddRef function for the IEcoXXXX interface
 * </description>
 *
 */
static uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_IEcoXXXX_AddRef(/* in */ struct IEcoXXXX* me) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[!output FIX_PROJECT_NAME]*));

    /* Pointer Validation */
    if (me == 0 ) {
        return -1; /* ERR_ECO_POINTER */
    }

[!if THREAD_SAFE]
    return atomicincrement_int32_t(&pCMe->m_cRef);
[!else]
    return ++pCMe->m_cRef;
[!endif]
}

/*
 *
 * <summary>
 *   Release Function
 * </summary>
 *
 * <description>
 *   Release function for the IEcoXXXX interface
 * </description>
 *
 */
static uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_IEcoXXXX_Release(/* in */ struct IEcoXXXX* me) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[!output FIX_PROJECT_NAME]*));

    /* Pointer Validation */
    if (me == 0 ) {
        return -1; /* ERR_ECO_POINTER */
    }

    /* Decrementing the component's reference count */
[!if THREAD_SAFE]
    atomicdecrement_int32_t(&pCMe->m_cRef);
[!else]
    --pCMe->m_cRef;
[!endif]

    /* If the count is zero, free the instance data */
    if ( pCMe->m_cRef == 0 ) {
        pCMe->Delete(pCMe);
        return 0;
    }
    return pCMe->m_cRef;
}
[!endif]

[!if ADD_CONNECTION_POINTS]
/*
 *
 * <summary>
 *   QueryInterface Function
 * </summary>
 *
 * <description>
 *   QueryInterface function for the IEcoConnectionPointContainer interface
 * </description>
 *
 */
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_QueryInterface(/* in */ struct IEcoConnectionPointContainer* me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[!output FIX_PROJECT_NAME]));

    if (me == 0 || ppv == 0) {
        return ERR_ECO_POINTER;
    }

    /* Validate and retrieve requested interface */
    if ( IsEqualUGUID(riid, &IID_I[!output FIX_PROJECT_NAME]) ) {
        *ppv = &pCMe->m_pVTblI[!output FIX_PROJECT_NAME];
        pCMe->m_pVTblI[!output FIX_PROJECT_NAME]->AddRef((I[!output FIX_PROJECT_NAME]*)pCMe);
    }
    else if ( IsEqualUGUID(riid, &IID_IEcoConnectionPointContainer) ) {
        *ppv = &pCMe->m_pVTblICPC;
        pCMe->m_pVTblI[!output FIX_PROJECT_NAME]->AddRef((I[!output FIX_PROJECT_NAME]*)pCMe);
    }
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown) ) {
        *ppv = &pCMe->m_pVTblI[!output FIX_PROJECT_NAME];
        pCMe->m_pVTblI[!output FIX_PROJECT_NAME]->AddRef((I[!output FIX_PROJECT_NAME]*)pCMe);
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
 *   AddRef function for the IEcoConnectionPointContainer interface
 * </description>
 *
 */
static uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_AddRef(/* in */ struct IEcoConnectionPointContainer* me) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[!output FIX_PROJECT_NAME]));

    /* Pointer Validation */
    if (me == 0 ) {
        return -1; /* ERR_ECO_POINTER */
    }

[!if THREAD_SAFE]
    return atomicincrement_int32_t(&pCMe->m_cRef);
[!else]
    return ++pCMe->m_cRef;
[!endif]
}

/*
 *
 * <summary>
 *   Release Function
 * </summary>
 *
 * <description>
 *   Release function for the IEcoConnectionPointContainer interface
 * </description>
 *
 */
static uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_Release(/* in */ struct IEcoConnectionPointContainer* me) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[!output FIX_PROJECT_NAME]));

    /* Pointer Validation */
    if (me == 0 ) {
        return -1; /* ERR_ECO_POINTER */
    }

    /* Decrementing the component's reference count */
[!if THREAD_SAFE]
    atomicdecrement_int32_t(&pCMe->m_cRef);
[!else]
    --pCMe->m_cRef;
[!endif]

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
 *   EnumConnectionPoints Function
 * </summary>
 *
 * <description>
 *   Function
 * </description>
 *
 */
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_EnumConnectionPoints(/* in */ struct IEcoConnectionPointContainer* me, /* out */ struct IEcoEnumConnectionPoints **ppEnum) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[!output FIX_PROJECT_NAME]));
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints* pCObj = 0;
    int16_t result = ERR_ECO_POINTER;

    if (me == 0 || ppEnum ==0 ) {
        return result;
    }

    pCObj = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints*)pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, sizeof(C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints));
    pCObj = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints*)pCMe->m_pIMem->pVTbl->Copy(pCMe->m_pIMem, pCObj, &g_xC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints, sizeof(C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]EnumConnectionPoints));
    pCObj->Create(pCObj, (IEcoUnknownPtr_t)pCMe->m_pISys);
    result = pCObj->Init(pCObj, (IEcoUnknownPtr_t)pCMe->m_pISys, (IEcoConnectionPointPtr_t)&pCMe->m_pISinkCP->m_pVTblICP);
    *ppEnum = (IEcoEnumConnectionPointsPtr_t)pCObj;

    return result;
}

/*
 *
 * <summary>
 *   FindConnectionPoint Function
 * </summary>
 *
 * <description>
 *   Function
 * </description>
 *
 */
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_FindConnectionPoint(/* in */ struct IEcoConnectionPointContainer* me, /* in */ const UGUID* riid, /* out */ struct IEcoConnectionPoint **ppCP) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[!output FIX_PROJECT_NAME]));
    int16_t result = ERR_ECO_POINTER;

    if (me == 0 || ppCP == 0 ) {
        return result;
    }

    if ( !IsEqualUGUID(riid, &IID_I[!output FIX_PROJECT_NAME]Events ) ) {
        *ppCP = 0;
        return -1; //ERR_ECO_OUTINTERFACE_NOCONNECTION;
    }

    if (pCMe->m_pISinkCP == 0) {
        return ERR_ECO_FAIL;
    }

    pCMe->m_pISinkCP->m_pVTblICP->AddRef((IEcoConnectionPointPtr_t)&pCMe->m_pISinkCP->m_pVTblICP);
    *ppCP = (IEcoConnectionPointPtr_t)&pCMe->m_pISinkCP->m_pVTblICP;

    return ERR_ECO_SUCCESES;
}

/*
 *
 * <summary>
 *   Fire_OnSearchStarted Function
 * </summary>
 *
 * <description>
 *   Callback interface invocation function
 * </description>
 *
 */
static int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_I[!output FIX_PROJECT_NAME]Events_Fire_OnMyCallback(/* in */ struct C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* me, /* in */ char_t* Name) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)me;
    int16_t result = ERR_ECO_POINTER;
    uint32_t count = 0;
    uint32_t index = 0;
    IEcoEnumConnections* pEnum = 0;
    I[!output FIX_PROJECT_NAME]Events* pIEvents = 0;
    EcoConnectionData cd;

    /* Pointer Validation */
    if (me == 0 ) {
        return result;
    }

    if (pCMe->m_pISinkCP != 0) {
        result = ((IEcoConnectionPoint*)pCMe->m_pISinkCP)->pVTbl->EnumConnections((IEcoConnectionPoint*)pCMe->m_pISinkCP, &pEnum);
        if ( (result == 0) && (pEnum != 0) ) {
            while (pEnum->pVTbl->Next(pEnum, 1, &cd, 0) == 0) {
                result = cd.pUnk->pVTbl->QueryInterface(cd.pUnk, &IID_I[!output FIX_PROJECT_NAME]Events, (void**)&pIEvents);
                if ( (result == 0) && (pIEvents != 0) ) {
                    result = pIEvents->pVTbl->OnMyCallback(pIEvents, Name);
                    pIEvents->pVTbl->Release(pIEvents);
                }
                cd.pUnk->pVTbl->Release(cd.pUnk);
            }
            pEnum->pVTbl->Release(pEnum);
        }
    }
    return result;
}
[!endif]

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
static int16_t ECOCALLMETHOD initC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE](/*in*/ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]Ptr_t me, /* in */ IEcoUnknownPtr_t pIUnkSystem) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)me;
    IEcoInterfaceBus1* pIBus = 0;
[!if ADD_AGGREGATION_OUTER]
    IEcoUnknown* pOuterUnknown = (IEcoUnknown*)me;
[!endif]

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

[!if ADD_CONNECTION_POINTS]
    /* Creating a connection point */
    pCMe->m_pISinkCP = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint*)pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, sizeof(C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint));
    pCMe->m_pISinkCP = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint*)pCMe->m_pIMem->pVTbl->Copy(pCMe->m_pIMem, pCMe->m_pISinkCP, &g_xC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint, sizeof(C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]ConnectionPoint));
    pCMe->m_pISinkCP->Create(pCMe->m_pISinkCP, (IEcoUnknownPtr_t)pCMe->m_pISys);
    result = pCMe->m_pISinkCP->Init(pCMe->m_pISinkCP, (IEcoUnknownPtr_t)pCMe->m_pISys, (IEcoConnectionPointContainerPtr_t)&pCMe->m_pVTblICPC, &IID_I[!output FIX_PROJECT_NAME]Events);
    if (result == 0 && pCMe->m_pISinkCP != 0) {
        result = ERR_ECO_SUCCESES;
    }
[!endif]

[!if ADD_AGGREGATION_OUTER]
    /* Creating an inner component with aggregation support */
    /* IMPORTANT: For aggregation, we pass IID IEcoUnknown */
    result = pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoXXXX, pOuterUnknown, &IID_IEcoUnknown, (void**) &pCMe->m_pIUnkInner);
[!endif]
[!if ADD_CONTAINMENT_OUTER]
    /* Creating an inner component (containment) */
    /*result = pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoXXXX, 0, &IID_IEcoXXXX, (void**) &pCMe->m_pIXXXX);*/
[!endif]

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
static int16_t ECOCALLMETHOD createC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE](/* in */ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoUnknownPtr_t pIUnkOuter) {
    int16_t result = ERR_ECO_POINTER;

    /* Pointer Validation */
    if (pCMe == 0) {
        return result; /* ERR_ECO_POINTER */
    }

[!if ADD_AGGREGATION_INNER]
    /* Nondelegating IEcoUnknown interface */
    pCMe->m_pVTblINondelegatingUnk = &g_x000000000000000000000000000000AAVTblUnk[!output GUID_CID_NAMESPACE];

    pCMe->m_pIUnkOuter = 0;
    /* If not aggregating, use the nondelegating IEcoUnknown interface */
    if (pIUnkOuter != 0) {
        pCMe->m_pIUnkOuter = pIUnkOuter;
    } else {
        pCMe->m_pIUnkOuter = (IEcoUnknown*)&pCMe->m_pVTblINondelegatingUnk;
    }
[!endif]

[!if ADD_AGGREGATION_OUTER]
    pCMe->m_pIUnkInner = 0;
[!endif]
[!if ADD_CONTAINMENT_OUTER]
    pCMe->m_pIXXXX = 0;
[!endif]

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
static void ECOCALLMETHOD deleteC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE](/* in */ C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]Ptr_t pCMe) {
    IEcoMemoryAllocator1* pIMem = 0;

    if (pCMe != 0 ) {
        pIMem = pCMe->m_pIMem;
        /* Freeing */
        if ( pCMe->m_Name != 0 ) {
            pIMem->pVTbl->Free(pIMem, pCMe->m_Name);
        }
[!if ADD_CONNECTION_POINTS]
        if (pCMe->m_pISinkCP != 0) {
            // Delete pCMe->m_pISinkCP;
            pCMe->m_pISinkCP = 0;
        }
[!endif]
        if ( pCMe->m_pISys != 0 ) {
            pCMe->m_pISys->pVTbl->Release(pCMe->m_pISys);
        }
        pIMem->pVTbl->Free(pIMem, pCMe);
        pIMem->pVTbl->Release(pIMem);
    }
}

/* I[!output FIX_PROJECT_NAME] Virtual Table */
I[!output FIX_PROJECT_NAME]VTbl g_x[!output GUID_IID_TARGET]VTbl[!output GUID_CID_NAMESPACE] = {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_QueryInterface,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_AddRef,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_Release,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_MyFunction
};
[!if ADD_AGGREGATION_INNER]
/* IEcoNondelegatingUnknown Virtual Table */
IEcoUnknownVTbl g_x000000000000000000000000000000AAVTblUnk[!output GUID_CID_NAMESPACE] = {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_NondelegatingQueryInterface,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_NondelegatingAddRef,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_NondelegatingRelease
};
[!endif]

[!if ADD_CONTAINMENT_OUTER]
/* IEcoXXXX Virtual Table */
IEcoXXXXVTbl g_xXXXXVTbl[!output GUID_CID_NAMESPACE] = {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_IEcoXXXX_QueryInterface,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_IEcoXXXX_AddRef,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_IEcoXXXX_Release
};
[!endif]

[!if ADD_CONNECTION_POINTS]
/* IEcoConnectionPointContainer Virtual Table */
IEcoConnectionPointContainerVTbl g_x0000000500000000C000000000000046VTblCPC[!output GUID_CID_NAMESPACE] = {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_QueryInterface,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_AddRef,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_Release,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_EnumConnectionPoints,
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_FindConnectionPoint
};
[!endif]

/* Object Instance */
C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE] g_xC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE] = {
    &g_x[!output GUID_IID_TARGET]VTbl[!output GUID_CID_NAMESPACE],
 [!if ADD_CONNECTION_POINTS]
    &g_x0000000500000000C000000000000046VTblCPC[!output GUID_CID_NAMESPACE],
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]_I[!output FIX_PROJECT_NAME]Events_Fire_OnMyCallback,
[!endif]   
    initC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE],
    createC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE],
    deleteC[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE],
    1, /* m_cRef */
    0, /* m_pISys */
    0, /* m_pISys */
    0  /* m_Name */
};
