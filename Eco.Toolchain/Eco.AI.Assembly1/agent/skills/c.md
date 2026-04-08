# CODE STYLE: HEADER TEMPLATES
Если попросят, то используй следующие шапки при генерации:

## File Header
/*
 * <character encoding> Cyrillic (UTF-8 with signature) - Codepage 65001 </character encoding>
 * <summary> </summary>
 * <description> </description>
 * <reference> </reference>
 * <author> Copyright (c) 2026 [AUTHOR]. All rights reserved. </author>
 */

## Function Header
/*
 * <summary> </summary>
 * <description> </description>
 */

# ID COMPONENT TEMPLATE (C)
При генерации файла `IdEco[Name].h` используй строго этот шаблон:

#ifndef __ID_[UPPER_PROJECT_NAME]_H__
#define __ID_[UPPER_PROJECT_NAME]_H__

#include "IEcoBase1.h"
#include "I[PROJECT_NAME].h"

/* [PROJECT_NAME] CID = [GUID_CID] */
#ifndef __CID_[PROJECT_NAME]
static const UGUID CID_[PROJECT_NAME] = [GUID_CID_FORMATED];
#endif /* __CID_[PROJECT_NAME] */

/* Component factory for dynamic and static layout */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_[GUID_CID_TARGET];
#endif

#endif /* __ID_[UPPER_PROJECT_NAME]_H__ */

# C INTERFACE TEMPLATE (Eco Model)
При генерации файла `IEco[Name].h` используй строго этот шаблон:

#ifndef __I_[UPPER_PROJECT_NAME]_H__
#define __I_[UPPER_PROJECT_NAME]_H__

#include "IEcoBase1.h"

/* I[PROJECT_NAME] IID = [GUID_IID] */
#ifndef __IID_I[PROJECT_NAME]
static const UGUID IID_I[PROJECT_NAME] = [GUID_IID_FORMATED];
#endif /* __IID_I[PROJECT_NAME] */

typedef struct I[PROJECT_NAME]* I[PROJECT_NAME]Ptr_t;

typedef struct I[PROJECT_NAME]VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ I[PROJECT_NAME]Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ I[PROJECT_NAME]Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ I[PROJECT_NAME]Ptr_t me);

    /* I[PROJECT_NAME] */
    int16_t (ECOCALLMETHOD *[METHOD_NAME])(/* in */ I[PROJECT_NAME]Ptr_t me, [METHOD_PARAMETERS]);

} I[PROJECT_NAME]VTbl, *I[PROJECT_NAME]VTblPtr_t;

interface I[PROJECT_NAME] {
    struct I[PROJECT_NAME]VTbl *pVTbl;
} I[PROJECT_NAME];

#endif /* __I_[UPPER_PROJECT_NAME]_H__ */

# C OBJECT IMPLEMENTATION TEMPLATE (Header)
При генерации заголовочного файла объекта `HeaderFiles/CEco[Name].h` используй этот шаблон. Обращай внимание на макросы и условную компиляцию:
#ifndef __C_[UPPER_PROJECT_NAME]_H__
#define __C_[UPPER_PROJECT_NAME]_H__

#include "I[FIX_PROJECT_NAME].h"
#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"
[!if ADD_CONNECTION_POINTS]
#include "IEcoEnumConnections.h"
#include "IEcoConnectionPointContainer.h"
#include "C[FIX_PROJECT_NAME]ConnectionPoint.h"
[!endif]
[!if ADD_CONTAINMENT_OUTER]
/*#include "IEcoXXXX.h"*/
[!endif]

typedef struct C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Ptr_t;

typedef struct C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE] {

    /* I[FIX_PROJECT_NAME] interface function table */
    I[FIX_PROJECT_NAME]VTbl* m_pVTblI[FIX_PROJECT_NAME];

[!if ADD_AGGREGATION_INNER]
    /* Nondelegating IEcoUnknown interface */
    IEcoUnknownVTbl* m_pVTblINondelegatingUnk;

[!endif]
[!if ADD_CONTAINMENT_OUTER]
    /* IEcoXXXX interface function table */
    IEcoXXXXVTbl* m_pVTblIXXXX;

[!endif]
[!if ADD_CONNECTION_POINTS]
    /* IEcoConnectionPointContainer interface function table */
    IEcoConnectionPointContainerVTbl* m_pVTblICPC;

    /* Helper functions for notifications */
    int16_t (*Fire_OnMyCallback)(/* in */ struct C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* me, /* in */ char_t* Name);

[!endif]

    /* Instance initialization */
    int16_t (ECOCALLMETHOD *Init)(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem);
    /* Instance creation */
    int16_t (ECOCALLMETHOD *Create)(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoUnknownPtr_t pIUnkOuter);
    /* Deletion */
    void (ECOCALLMETHOD *Delete)(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Ptr_t pCMe);


    /* Reference counter */
    uint32_t m_cRef;

    /* Interface for memory operations */
    IEcoMemoryAllocator1* m_pIMem;

    /* System interface */
    IEcoSystem1* m_pISys;

[!if ADD_CONNECTION_POINTS]
    /* Connection point */
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint* m_pISinkCP;

[!endif]
[!if ADD_AGGREGATION_INNER]
    /* Delegating IEcoUnknown, points to the outer or nondelegating IEcoUnknown */
    IEcoUnknown* m_pIUnkOuter;

[!endif]
[!if ADD_AGGREGATION_OUTER]
    /* Pointer to the inner component's IEcoUnknown */
    IEcoUnknown* m_pIUnkInner;

[!endif]
[!if ADD_CONTAINMENT_OUTER]
    /* Pointer to the included component's IEcoXXXX interface */
    IEcoXXXX* m_pIXXXX;

[!endif]
    /* Instance data */
    char_t* m_Name;

} C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE];

#endif /* __C_[UPPER_PROJECT_NAME]_H__ */

# C OBJECT IMPLEMENTATION TEMPLATE (Source)
При генерации файлов в `SourceFiles/CEco[Name].c` строго следуй логике шаблона:

### Шаблон:
#include "IEcoSystem1.h"
#include "IEcoInterfaceBus1.h"
#include "IEcoInterfaceBus1MemExt.h"
#include "C[FIX_PROJECT_NAME].h"
[!if ADD_CONNECTION_POINTS]
#include "C[FIX_PROJECT_NAME]EnumConnectionPoints.h"
#include "IEcoConnectionPointContainer.h"
[!endif]


extern C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints g_xC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints;
extern C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint g_xC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint;

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_QueryInterface(/* in */ I[FIX_PROJECT_NAME]Ptr_t me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)me;

    /* Pointer Validation */
    if (me == 0 || ppv == 0) {
        return ERR_ECO_POINTER;
    }

[!if ADD_AGGREGATION_INNER]
    return pCMe->m_pIUnkOuter->pVTbl->QueryInterface(pCMe->m_pIUnkOuter, riid, ppv);
[!else]
    /* Validate and retrieve requested interface */
    if ( IsEqualUGUID(riid, &IID_I[FIX_PROJECT_NAME]) ) {
        *ppv = &pCMe->m_pVTblI[FIX_PROJECT_NAME];
        pCMe->m_pVTblI[FIX_PROJECT_NAME]->AddRef((I[FIX_PROJECT_NAME]*)pCMe);
    }
[!if ADD_CONTAINMENT_OUTER]
    else if (IsEqualUGUID(riid, &IID_IEcoXXX)) {
        *ppv = &pCMe->m_pVTblIXXXX;
        pCMe->m_pVTblI[FIX_PROJECT_NAME]->AddRef((I[FIX_PROJECT_NAME]*)pCMe);
    }
[!endif]	
[!if ADD_CONNECTION_POINTS]
    else if ( IsEqualUGUID(riid, &IID_IEcoConnectionPointContainer) ) {
        *ppv = &pCMe->m_pVTblICPC;
        pCMe->m_pVTblICPC->AddRef((IEcoConnectionPointContainer*)pCMe);
    }
[!endif]
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown) ) {
        *ppv = &pCMe->m_pVTblI[FIX_PROJECT_NAME];
        pCMe->m_pVTblI[FIX_PROJECT_NAME]->AddRef((I[FIX_PROJECT_NAME]*)pCMe);
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

static uint32_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_AddRef(/* in */ I[FIX_PROJECT_NAME]Ptr_t me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)me;

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

static uint32_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_Release(/* in */ I[FIX_PROJECT_NAME]Ptr_t me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)me;

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

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_MyFunction(/* in */ I[FIX_PROJECT_NAME]Ptr_t me, /* in */ char_t* Name, /* out */ char_t** copyName) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)me;
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
static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_NondelegatingQueryInterface(/* in */ I[FIX_PROJECT_NAME]Ptr_t me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[FIX_PROJECT_NAME]*));

    /* Pointer Validation */
    if (me == 0 || ppv == 0) {
        return ERR_ECO_POINTER;
    }

    /* Validate and retrieve requested interface */
    if ( IsEqualUGUID(riid, &IID_I[FIX_PROJECT_NAME]) ) {
        *ppv = &pCMe->m_pVTblI[FIX_PROJECT_NAME];
        pCMe->m_pVTblI[FIX_PROJECT_NAME]->AddRef((I[FIX_PROJECT_NAME]*)pCMe);
    }
[!if ADD_CONNECTION_POINTS]
    else if ( IsEqualUGUID(riid, &IID_IEcoConnectionPointContainer) ) {
        *ppv = &pCMe->m_VtblICPC;
        pCMe->m_pVTblICPC->AddRef((IEcoConnectionPointContainer*)pCMe);
    }
[!endif]
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown) ) {
        *ppv = &pCMe->m_pVTblI[FIX_PROJECT_NAME];
        pCMe->m_pVTblI[FIX_PROJECT_NAME]->AddRef((I[FIX_PROJECT_NAME]*)pCMe);
    }
    else {
        *ppv = 0;
        return ERR_ECO_NOINTERFACE;
    }
    return ERR_ECO_SUCCESES;
}

static uint32_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_NondelegatingAddRef(/* in */ I[FIX_PROJECT_NAME]Ptr_t me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[FIX_PROJECT_NAME]*));

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

static uint32_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_NondelegatingRelease(/* in */ I[FIX_PROJECT_NAME]Ptr_t me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[FIX_PROJECT_NAME]*));

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
static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_IEcoXXXX_QueryInterface(/* in */ struct IEcoXXXX* me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[FIX_PROJECT_NAME]*));

    /* Pointer Validation */
    if (me == 0 || ppv == 0) {
        return ERR_ECO_POINTER;
    }

    /* Validate and retrieve requested interface */
    if ( IsEqualUGUID(riid, &IID_I[FIX_PROJECT_NAME]) ) {
        *ppv = &pCMe->m_pVTblI[FIX_PROJECT_NAME];
        pCMe->m_pVTblI[FIX_PROJECT_NAME]->AddRef((I[FIX_PROJECT_NAME]*)pCMe);
    }
    else if (IsEqualUGUID(riid, &IID_IEcoXXX)) {
        *ppv = &pCMe->m_pVTblIXXXX;
        pCMe->m_pVTblI[FIX_PROJECT_NAME]->AddRef((I[FIX_PROJECT_NAME]*)pCMe);
    }	
[!if ADD_CONNECTION_POINTS]
    else if ( IsEqualUGUID(riid, &IID_IEcoConnectionPointContainer) ) {
        *ppv = &pCMe->m_VtblICPC;
        pCMe->m_pVTblICPC->AddRef((IEcoConnectionPointContainer*)pCMe);
    }
[!endif]
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown) ) {
        *ppv = &pCMe->m_pVTblI[FIX_PROJECT_NAME];
        pCMe->m_pVTblI[FIX_PROJECT_NAME]->AddRef((I[FIX_PROJECT_NAME]*)pCMe);
    }
    else {
        *ppv = 0;
        return ERR_ECO_NOINTERFACE;
    }
    return ERR_ECO_SUCCESES;
}

static uint32_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_IEcoXXXX_AddRef(/* in */ struct IEcoXXXX* me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[FIX_PROJECT_NAME]*));

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

static uint32_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_IEcoXXXX_Release(/* in */ struct IEcoXXXX* me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[FIX_PROJECT_NAME]*));

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
static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_QueryInterface(/* in */ struct IEcoConnectionPointContainer* me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[FIX_PROJECT_NAME]));

    if (me == 0 || ppv == 0) {
        return ERR_ECO_POINTER;
    }

    /* Validate and retrieve requested interface */
    if ( IsEqualUGUID(riid, &IID_I[FIX_PROJECT_NAME]) ) {
        *ppv = &pCMe->m_pVTblI[FIX_PROJECT_NAME];
        pCMe->m_pVTblI[FIX_PROJECT_NAME]->AddRef((I[FIX_PROJECT_NAME]*)pCMe);
    }
    else if ( IsEqualUGUID(riid, &IID_IEcoConnectionPointContainer) ) {
        *ppv = &pCMe->m_pVTblICPC;
        pCMe->m_pVTblI[FIX_PROJECT_NAME]->AddRef((I[FIX_PROJECT_NAME]*)pCMe);
    }
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown) ) {
        *ppv = &pCMe->m_pVTblI[FIX_PROJECT_NAME];
        pCMe->m_pVTblI[FIX_PROJECT_NAME]->AddRef((I[FIX_PROJECT_NAME]*)pCMe);
    }
    else {
        *ppv = 0;
        return ERR_ECO_NOINTERFACE;
    }

    return ERR_ECO_SUCCESES;
}

static uint32_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_AddRef(/* in */ struct IEcoConnectionPointContainer* me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[FIX_PROJECT_NAME]));

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

static uint32_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_Release(/* in */ struct IEcoConnectionPointContainer* me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[FIX_PROJECT_NAME]));

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

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_EnumConnectionPoints(/* in */ struct IEcoConnectionPointContainer* me, /* out */ struct IEcoEnumConnectionPoints **ppEnum) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[FIX_PROJECT_NAME]));
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints* pCObj = 0;
    int16_t result = ERR_ECO_POINTER;

    if (me == 0 || ppEnum ==0 ) {
        return result;
    }

    pCObj = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints*)pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, sizeof(C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints));
    pCObj = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints*)pCMe->m_pIMem->pVTbl->Copy(pCMe->m_pIMem, pCObj, &g_xC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints, sizeof(C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints));
    pCObj->Create(pCObj, (IEcoUnknownPtr_t)pCMe->m_pISys);
    result = pCObj->Init(pCObj, (IEcoUnknownPtr_t)pCMe->m_pISys, (IEcoConnectionPointPtr_t)&pCMe->m_pISinkCP->m_pVTblICP);
    *ppEnum = (IEcoEnumConnectionPointsPtr_t)pCObj;

    return result;
}

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_FindConnectionPoint(/* in */ struct IEcoConnectionPointContainer* me, /* in */ const UGUID* riid, /* out */ struct IEcoConnectionPoint **ppCP) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)((uint64_t)me - sizeof(struct I[FIX_PROJECT_NAME]));
    int16_t result = ERR_ECO_POINTER;

    if (me == 0 || ppCP == 0 ) {
        return result;
    }

    if ( !IsEqualUGUID(riid, &IID_I[FIX_PROJECT_NAME]Events ) ) {
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

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_I[FIX_PROJECT_NAME]Events_Fire_OnMyCallback(/* in */ struct C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* me, /* in */ char_t* Name) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)me;
    int16_t result = ERR_ECO_POINTER;
    uint32_t count = 0;
    uint32_t index = 0;
    IEcoEnumConnections* pEnum = 0;
    I[FIX_PROJECT_NAME]Events* pIEvents = 0;
    EcoConnectionData cd;

    /* Pointer Validation */
    if (me == 0 ) {
        return result;
    }

    if (pCMe->m_pISinkCP != 0) {
        result = ((IEcoConnectionPoint*)pCMe->m_pISinkCP)->pVTbl->EnumConnections((IEcoConnectionPoint*)pCMe->m_pISinkCP, &pEnum);
        if ( (result == 0) && (pEnum != 0) ) {
            while (pEnum->pVTbl->Next(pEnum, 1, &cd, 0) == 0) {
                result = cd.pUnk->pVTbl->QueryInterface(cd.pUnk, &IID_I[FIX_PROJECT_NAME]Events, (void**)&pIEvents);
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

static int16_t ECOCALLMETHOD initC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE](/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Ptr_t me, /* in */ IEcoUnknownPtr_t pIUnkSystem) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)me;
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
    pCMe->m_pISinkCP = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint*)pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, sizeof(C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint));
    pCMe->m_pISinkCP = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint*)pCMe->m_pIMem->pVTbl->Copy(pCMe->m_pIMem, pCMe->m_pISinkCP, &g_xC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint, sizeof(C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint));
    pCMe->m_pISinkCP->Create(pCMe->m_pISinkCP, (IEcoUnknownPtr_t)pCMe->m_pISys);
    result = pCMe->m_pISinkCP->Init(pCMe->m_pISinkCP, (IEcoUnknownPtr_t)pCMe->m_pISys, (IEcoConnectionPointContainerPtr_t)&pCMe->m_pVTblICPC, &IID_I[FIX_PROJECT_NAME]Events);
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

static int16_t ECOCALLMETHOD createC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE](/* in */ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Ptr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoUnknownPtr_t pIUnkOuter) {
    int16_t result = ERR_ECO_POINTER;

    /* Pointer Validation */
    if (pCMe == 0) {
        return result; /* ERR_ECO_POINTER */
    }

[!if ADD_AGGREGATION_INNER]
    /* Nondelegating IEcoUnknown interface */
    pCMe->m_pVTblINondelegatingUnk = &g_x000000000000000000000000000000AAVTblUnk[GUID_CID_NAMESPACE];

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

static void ECOCALLMETHOD deleteC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE](/* in */ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Ptr_t pCMe) {
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

/* I[FIX_PROJECT_NAME] Virtual Table */
I[FIX_PROJECT_NAME]VTbl g_x[GUID_IID_TARGET]VTbl[GUID_CID_NAMESPACE] = {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_QueryInterface,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_AddRef,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_Release,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_MyFunction
};
[!if ADD_AGGREGATION_INNER]
/* IEcoNondelegatingUnknown Virtual Table */
IEcoUnknownVTbl g_x000000000000000000000000000000AAVTblUnk[GUID_CID_NAMESPACE] = {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_NondelegatingQueryInterface,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_NondelegatingAddRef,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_NondelegatingRelease
};
[!endif]

[!if ADD_CONTAINMENT_OUTER]
/* IEcoXXXX Virtual Table */
IEcoXXXXVTbl g_xXXXXVTbl[GUID_CID_NAMESPACE] = {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_IEcoXXXX_QueryInterface,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_IEcoXXXX_AddRef,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_IEcoXXXX_Release
};
[!endif]

[!if ADD_CONNECTION_POINTS]
/* IEcoConnectionPointContainer Virtual Table */
IEcoConnectionPointContainerVTbl g_x0000000500000000C000000000000046VTblCPC[GUID_CID_NAMESPACE] = {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_QueryInterface,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_AddRef,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_Release,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_EnumConnectionPoints,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_IEcoConnectionPointContainer_FindConnectionPoint
};
[!endif]

/* Object Instance */
C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE] g_xC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE] = {
    &g_x[GUID_IID_TARGET]VTbl[GUID_CID_NAMESPACE],
 [!if ADD_CONNECTION_POINTS]
    &g_x0000000500000000C000000000000046VTblCPC[GUID_CID_NAMESPACE],
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]_I[FIX_PROJECT_NAME]Events_Fire_OnMyCallback,
[!endif]   
    initC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE],
    createC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE],
    deleteC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE],
    1, /* m_cRef */
    0, /* m_pISys */
    0, /* m_pISys */
    0  /* m_Name */
};

# C COMPONENT FACTORY TEMPLATE (Header)
При создании фабрики компонента (`HeaderFiles/CEco[Name]Factory.h`) следуй строгому шаблону:

## Заголовочный файл Фабрики
- **Structure**: Фабрика должна содержать таблицу виртуальных функций `IEcoComponentFactoryVTbl`.
- **Metadata**: Поля `m_Name[64]`, `m_Version[16]`, `m_Manufacturer[64]` обязательны для заполнения метаданными компонента.

### Шаблон:
#ifndef __C_[UPPER_PROJECT_NAME]_FACTORY_H__
#define __C_[UPPER_PROJECT_NAME]_FACTORY_H__

#include "IEcoSystem1.h"

typedef struct C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory {

    /* IEcoComponentFactory interface function table */
    IEcoComponentFactoryVTbl* m_pVTblICF;

    /* Reference counter */
    uint32_t m_cRef;

    /* Component data for the factory */
    char_t m_Name[64];
    char_t m_Version[16];
    char_t m_Manufacturer[64];

} C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory;

#endif /* __C_[UPPER_PROJECT_NAME]_FACTORY_H__ */

# C COMPONENT FACTORY TEMPLATE IMPLEMENTATION (Source)

### Шаблон:
#include "IEcoSystem1.h"
#include "IEcoInterfaceBus1.h"
#include "IEcoInterfaceBus1MemExt.h"

#include "C[FIX_PROJECT_NAME].h"
#include "C[FIX_PROJECT_NAME]Factory.h"

extern C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE] g_xC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE];

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory_QueryInterface(IEcoComponentFactory* me, const UGUID* riid, void** ppv) {
    if ( IsEqualUGUID(riid, &IID_IEcoUnknown) || IsEqualUGUID(riid, &IID_IEcoComponentFactory) ) {
        *ppv = me;
    }
    else {
        *ppv = 0;
        return ERR_ECO_NOINTERFACE;
    }
    ((IEcoUnknown*)(*ppv))->pVTbl->AddRef((IEcoUnknown*)*ppv);

    return ERR_ECO_SUCCESES;
}

static uint32_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory_AddRef(/* in */ IEcoComponentFactory* me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory*)me;

    if (me == 0 ) {
        return -1; /* ERR_ECO_POINTER */
    }

[!if THREAD_SAFE]
    return atomicincrement_int32_t(&pCMe->m_cRef);
[!else]
    return ++pCMe->m_cRef;
[!endif]
}

static uint32_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory_Release(/* in */ IEcoComponentFactory* me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory*)me;

    if (me == 0 ) {
        return -1; /* ERR_ECO_POINTER */
    }

    /* Decrementing the component reference counter */
[!if THREAD_SAFE]
    atomicdecrement_int32_t(&pCMe->m_cRef);
[!else]
    --pCMe->m_cRef;
[!endif]

    /* If the counter is zeroed, free the instance data */
    if ( pCMe->m_cRef == 0 ) {
        return 0;
    }
    return pCMe->m_cRef;
}

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory_Init(/* in */ struct IEcoComponentFactory* me, /* in */ struct IEcoUnknown *pIUnkSystem, /* in */ void* pv) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory*)me;
    int16_t result = ERR_ECO_POINTER;

    if (me == 0 ) {
        return result;
    }

    /* Initializing the component with parameters */

    return result;
}

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory_Alloc(/* in */ struct IEcoComponentFactory* me, /* in */ struct IEcoUnknown *pISystem, /* in */ struct IEcoUnknown *pIUnknownOuter, /* in */ const UGUID* riid, /* out */ void** ppv) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory*)me;
    IEcoUnknown* pIUnk = 0;
    int16_t result = ERR_ECO_POINTER;
    IEcoSystem1* pISys = 0;
    IEcoInterfaceBus1* pIBus = 0;
    IEcoInterfaceBus1MemExt* pIMemExt = 0;
    IEcoMemoryAllocator1* pIMem = 0;
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]* pCObj = 0;
    UGUID* rcid = (UGUID*)&CID_EcoMemoryManager1;

    if (me == 0 || pISystem == 0 ) {
        return result; /* ERR_ECO_POINTER */
    }

    /* Aggregation provided that IID is IID_IEcoUnknown */
    if ( ( pIUnknownOuter != 0 ) && !IsEqualUGUID(riid, &IID_IEcoUnknown ) ) {
        /* aggregation not supported */
        return ERR_ECO_NOAGGREGATION;
    }

    /* Getting the application system interface */
    result = pISystem->pVTbl->QueryInterface(pISystem, &GID_IEcoSystem, (void **)&pISys);
    /* Check */
    if (result != 0 || pISys == 0) {
        return ERR_ECO_NOSYSTEM;
    }

    /* Getting the interface for working with the interface bus */
    result = pISys->pVTbl->QueryInterface(pISys, &IID_IEcoInterfaceBus1, (void **)&pIBus);
    /* Check */
    if (result != 0 || pIBus == 0) {
        pISys->pVTbl->Release(pISys);
        return ERR_ECO_NOBUS;
    }

    /* Getting the component ID for memory operations */
    result = pIBus->pVTbl->QueryInterface(pIBus, &IID_IEcoInterfaceBus1MemExt, (void**)&pIMemExt);
    if (result == 0 && pIMemExt != 0) {
        rcid = (UGUID*)pIMemExt->pVTbl->get_Manager(pIMemExt);
        pIMemExt->pVTbl->Release(pIMemExt);
    }

    /* Getting the memory allocator interface */
    pIBus->pVTbl->QueryComponent(pIBus, rcid, 0, &IID_IEcoMemoryAllocator1, (void**) &pIMem);
    /* Check */
    if (result != 0 || pIMem == 0) {
        /* Freeing in case of an error */
        pIBus->pVTbl->Release(pIBus);
        pISys->pVTbl->Release(pISys);
        return ERR_ECO_GET_MEMORY_ALLOCATOR;
    }

    /* Allocating memory for instance data */
    pCObj = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)pIMem->pVTbl->Alloc(pIMem, sizeof(C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]));
    if (pCObj == 0) {
        /* Freeing in case of an error */
        pIBus->pVTbl->Release(pIBus);
        pISys->pVTbl->Release(pISys);
        return ERR_ECO_OUTOFMEMORY;
    }

    /* Forming instance data */
    pCObj = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]*)pIMem->pVTbl->Copy(pIMem, pCObj, &g_xC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE], sizeof(C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]));

    /* Component creation */
    pCObj->Create(pCObj, pISystem, pIUnknownOuter);

    /* Component initialization */
    result = pCObj->Init(pCObj, pISystem);

    /* Getting a pointer to the interface */
    pIUnk = (IEcoUnknown*)pCObj;
    result = pIUnk->pVTbl->QueryInterface(pIUnk, riid, ppv);

    /* Decrementing the reference requested by the Component Factory */
    pIUnk->pVTbl->Release(pIUnk);

    return result;
}

static char_t* ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory_get_Name(/* in */ struct IEcoComponentFactory* me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory*)me;

    if (me == 0 ) {
        return 0; /* ERR_ECO_POINTER */
    }

    return pCMe->m_Name;
}

static char_t* ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory_get_Version(/* in */ struct IEcoComponentFactory* me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory*)me;

    if (me == 0 ) {
        return 0; /* ERR_ECO_POINTER */
    }

    return pCMe->m_Version;
}

static char_t* ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory_get_Manufacturer(/* in */ struct IEcoComponentFactory* me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory*)me;

    if (me == 0 ) {
        return 0; /* ERR_ECO_POINTER */
    }

    return pCMe->m_Manufacturer;
}

/* Create Virtual Table */
IEcoComponentFactoryVTbl g_x[GUID_CID_TARGET]FactoryVTbl = {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory_QueryInterface,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory_AddRef,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory_Release,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory_Alloc,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory_Init,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory_get_Name,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory_get_Version,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory_get_Manufacturer
};

C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]Factory g_x[GUID_CID_TARGET]Factory = {
    &g_x[GUID_CID_TARGET]FactoryVTbl,
    0,
    "[FIX_PROJECT_NAME]\0",
    "1.0.0.0\0",
    "[COMPANY]\0"
};

#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr() {
    return (IEcoComponentFactory*)&g_x[GUID_CID_TARGET]Factory;
};
#elif ECO_LIB
IEcoComponentFactory* GetIEcoComponentFactoryPtr_[GUID_CID_TARGET] = (IEcoComponentFactory*)&g_x[GUID_CID_TARGET]Factory;
#endif

# ECO APP/UNIT-TEST GENERATION (EcoMain)

### Шаблон:
#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"
#include "IdEcoInterfaceBus1.h"
#include "IdEcoFileSystemManagement1.h"
[!if UNIT_TEST_PROJECT]
#include "Id[FIX_PROJECT_NAME].h"
[!endif]
[!if ADD_CONNECTION_POINTS]
#include "C[FIX_PROJECT_NAME]Sink.h"
#include "IEcoConnectionPointContainer.h"
[!endif]

int16_t EcoMain(IEcoUnknown* pIUnk) {
    int16_t result = -1;
    /* Pointer to the system interface */
    IEcoSystem1* pISys = 0;
    /* Pointer to the interface for working with the system interface bus */
    IEcoInterfaceBus1* pIBus = 0;
    /* Pointer to the memory management interface */
    IEcoMemoryAllocator1* pIMem = 0;
    char_t* name = 0;
[!if UNIT_TEST_PROJECT]
    char_t* copyName = 0;
    /* Pointer to the tested interface */
    I[FIX_PROJECT_NAME]* pI[FIX_PROJECT_NAME] = 0;
[!endif]
[!if ADD_CONNECTION_POINTS]
    /* Pointer to the connection points container interface */
    IEcoConnectionPointContainer* pICPC = 0;
    /* Pointer to the connection point interface */
    IEcoConnectionPoint* pICP = 0;
    /* Pointer to the reverse interface (sink) */
    I[FIX_PROJECT_NAME]Events* pI[FIX_PROJECT_NAME]Sink = 0;
    IEcoUnknown* pISinkUnk = 0;
    uint32_t cAdvise = 0;
[!endif]

    /* System interface check and creation */
    if (pISys == 0) {
        result = pIUnk->pVTbl->QueryInterface(pIUnk, &GID_IEcoSystem, (void **)&pISys);
        if (result != 0 && pISys == 0) {
        /* Free the system interface in case of an error */
            goto Release;
        }
    }

    /* Getting the interface for working with the interface bus */
    result = pISys->pVTbl->QueryInterface(pISys, &IID_IEcoInterfaceBus1, (void **)&pIBus);
    if (result != 0 || pIBus == 0) {
        /* Free in case of an error */
        goto Release;
    }
[!if UNIT_TEST_PROJECT]
#ifdef ECO_LIB
    /* Registration of a static component for working with the list */
    result = pIBus->pVTbl->RegisterComponent(pIBus, &CID_[FIX_PROJECT_NAME], (IEcoUnknown*)GetIEcoComponentFactoryPtr_[GUID_CID_TARGET]);
    if (result != 0 ) {
        /* Free in case of an error */
        goto Release;
    }
#endif
[!endif]
    /* Getting the memory management interface */
    result = pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoMemoryManager1, 0, &IID_IEcoMemoryAllocator1, (void**) &pIMem);

    /* Check */
    if (result != 0 || pIMem == 0) {
        /* Free the system interface in case of an error */
        goto Release;
    }

    /* Memory block allocation */
    name = (char_t *)pIMem->pVTbl->Alloc(pIMem, 10);

    /* Fill the memory block */
    pIMem->pVTbl->Fill(pIMem, name, 'a', 9);

[!if UNIT_TEST_PROJECT]

    /* Getting the tested interface */
    result = pIBus->pVTbl->QueryComponent(pIBus, &CID_[FIX_PROJECT_NAME], 0, &IID_I[FIX_PROJECT_NAME], (void**) &pI[FIX_PROJECT_NAME]);
    if (result != 0 || pI[FIX_PROJECT_NAME] == 0) {
        /* Free interfaces in case of an error */
        goto Release;
    }

[!if ADD_CONNECTION_POINTS]
    /* Checking support for reverse interface connections */
    result = pI[FIX_PROJECT_NAME]->pVTbl->QueryInterface(pI[FIX_PROJECT_NAME], &IID_IEcoConnectionPointContainer, (void **)&pICPC);
    if (result != 0 || pICPC == 0) {
        /* Free interfaces in case of an error */
        goto Release;
    }

    /* Request to get the connection point interface */
    result = pICPC->pVTbl->FindConnectionPoint(pICPC, &IID_I[FIX_PROJECT_NAME]Events, &pICP);
    if (result != 0 || pICP == 0) {
        /* Free interfaces in case of an error */
        goto Release;
    }
    /* Free the interface */
    pICPC->pVTbl->Release(pICPC);

    /* Create an instance of the reverse interface */
    result = createC[FIX_PROJECT_NAME]Sink(pIMem, (I[FIX_PROJECT_NAME]Events**)&pI[FIX_PROJECT_NAME]Sink);

    if (pI[FIX_PROJECT_NAME]Sink != 0) {
        result = pI[FIX_PROJECT_NAME]Sink->pVTbl->QueryInterface(pI[FIX_PROJECT_NAME]Sink, &IID_IEcoUnknown,(void **)&pISinkUnk);
        if (result != 0 || pISinkUnk == 0) {
            /* Free interfaces in case of an error */
            goto Release;
        }
        /* Connection (Advise) */
        result = pICP->pVTbl->Advise(pICP, pISinkUnk, &cAdvise);
        /* Check */
        if (result == 0 && cAdvise == 1) {
            /* Code can be added here */
        }
        /* Free the interface */
        pISinkUnk->pVTbl->Release(pISinkUnk);
    }

[!endif]

    result = pI[FIX_PROJECT_NAME]->pVTbl->MyFunction(pI[FIX_PROJECT_NAME], name, &copyName);

[!endif]

    /* Free the memory block */
    pIMem->pVTbl->Free(pIMem, name);

Release:

    /* Free the interface for working with the interface bus */
    if (pIBus != 0) {
        pIBus->pVTbl->Release(pIBus);
    }

    /* Free the memory management interface */
    if (pIMem != 0) {
        pIMem->pVTbl->Release(pIMem);
    }

[!if UNIT_TEST_PROJECT]
    /* Free the tested interface */
    if (pI[FIX_PROJECT_NAME] != 0) {
        pI[FIX_PROJECT_NAME]->pVTbl->Release(pI[FIX_PROJECT_NAME]);
    }

[!endif]

    /* Free the system interface */
    if (pISys != 0) {
        pISys->pVTbl->Release(pISys);
    }

    return result;
}

# ECO CONNECTION POINTS (Infrastructure)
При реализации механизма событий используй заголовочный файл `HeaderFiles/CEco[Name]ConnectionPoint.h` по следующему шаблону:

## Шаблон ConnectionPoint (Header)
#ifndef __C_[UPPER_PROJECT_NAME]_CONNECTION_POINT_H__
#define __C_[UPPER_PROJECT_NAME]_CONNECTION_POINT_H__

#include "IEcoConnectionPoint.h"
#include "IEcoConnectionPointContainer.h"
#include "IdEcoList1.h"
#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"

typedef struct C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint* C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPointPtr_t;

typedef struct C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint {

    IEcoConnectionPointVTbl* m_pVTblICP;


    int16_t (ECOCALLMETHOD *Init)(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPointPtr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoConnectionPointContainer* pICPC, /* in */ const UGUID* riid);
    int16_t (ECOCALLMETHOD *Create)(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPointPtr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem);
    void (ECOCALLMETHOD *Delete)(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPointPtr_t pCMe);

    IEcoConnectionPointContainer* m_pICPC;
    UGUID* m_piid;
    uint32_t m_cNextCookie;
    IEcoList1* m_pSinkList;
    IEcoMemoryAllocator1* m_pIMem;
    IEcoSystem1* m_pISys;

} C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint;

#endif /* __C_[UPPER_PROJECT_NAME]_CONNECTION_POINT_H__ */


## Шаблон ConnectionPoint (Source)
#include "IEcoInterfaceBus1.h"
#include "IEcoInterfaceBus1MemExt.h"
#include "C[FIX_PROJECT_NAME]ConnectionPoint.h"
#include "C[FIX_PROJECT_NAME]EnumConnections.h"

extern C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections g_xC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections;

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint_QueryInterface(/* in */ struct IEcoConnectionPoint* me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint*)me;

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

static uint32_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint_AddRef(/* in */ struct IEcoConnectionPoint* me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint*)me;

    if (me == 0 ) {
        return -1;
    }

    return pCMe->m_pICPC->pVTbl->AddRef(pCMe->m_pICPC);
}

static uint32_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint_Release(/* in */ struct IEcoConnectionPoint* me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint*)me;

    if (me == 0 ) {
        return -1;
    }

    return pCMe->m_pICPC->pVTbl->Release(pCMe->m_pICPC);
}

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint_GetConnectionInterface(/* in */ struct IEcoConnectionPoint* me, /* out */ UGUID *pIID) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint*)me;

    if (me == 0 || pIID == 0) {
        return -1;
    }

    pIID = (UGUID *)&pCMe->m_piid;
    return 0;
}

 static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint_GetConnectionPointContainer(/* in */ struct IEcoConnectionPoint* me, /* out */ struct IEcoConnectionPointContainer **ppICPC) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint*)me;

    if (me == 0 || ppICPC == 0) {
        return -1;
    }

    *ppICPC = pCMe->m_pICPC;
    pCMe->m_pICPC->pVTbl->AddRef(pCMe->m_pICPC);

    return 0;
}

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint_Advise(/* in */ struct IEcoConnectionPoint* me, /* in */ struct IEcoUnknown *pUnkSink, /* out */ uint32_t *pcCookie) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint*)me;
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

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint_Unadvise(/* in */ struct IEcoConnectionPoint* me, /* in */ uint32_t cCookie) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint*)me;
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

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint_EnumConnections(/* in */ struct IEcoConnectionPoint* me, /* out */ struct IEcoEnumConnections **ppEnum) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint*)me;
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections* pCObj = 0;
    int16_t result = ERR_ECO_POINTER;

    if (me == 0 || ppEnum ==0 ) {
        return result;
    }

    pCObj = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections*)pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, sizeof(C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections));
    pCObj = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections*)pCMe->m_pIMem->pVTbl->Copy(pCMe->m_pIMem, pCObj, &g_xC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections, sizeof(C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections));
    pCObj->Create(pCObj, (IEcoUnknownPtr_t)pCMe->m_pISys);
    result = pCObj->Init(pCObj, (IEcoUnknownPtr_t)pCMe->m_pISys, pCMe->m_pSinkList);
    *ppEnum = (IEcoEnumConnectionsPtr_t)pCObj;
    
    return result;
}

static int16_t ECOCALLMETHOD initC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPointPtr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoConnectionPointContainer* pICPC, /* in */ const UGUID* riid) {
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

static int16_t ECOCALLMETHOD createC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPointPtr_t pCMe, /* in */ IEcoUnknown* pIUnkSystem) {
    int16_t result = ERR_ECO_POINTER;

    /* Pointer Validation */
    if (pCMe == 0) {
        return result; /* ERR_ECO_POINTER */
    }


    return ERR_ECO_SUCCESES;
}

static void ECOCALLMETHOD deleteC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPointPtr_t pCMe) {
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
IEcoConnectionPointVTbl g_x0000000300000000C000000000000046VTblCP[GUID_CID_NAMESPACE] = {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint_QueryInterface,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint_AddRef,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint_Release,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint_GetConnectionInterface,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint_GetConnectionPointContainer,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint_Advise,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint_Unadvise,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint_EnumConnections
};

/* Object Instance */
C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint g_xC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint = {
    &g_x0000000300000000C000000000000046VTblCP[GUID_CID_NAMESPACE],
    initC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint,
    createC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint,
    deleteC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]ConnectionPoint,
    0, /* m_pICPC */
    0, /* m_piid */
    0, /* m_cNextCookie */
    0, /* m_pSinkList */
    0, /* m_pIMem */  
    0  /* m_pISys */
};

# ECO ENUM CONNECTION POINTS (Enumerator)
При реализации перечислителя точек подключения используй заголовочный файл `HeaderFiles/CEco[Name]EnumConnectionPoints.h`:

## Шаблон EnumConnectionPoints (Header)
#ifndef __C_[UPPER_PROJECT_NAME]_ENUM_CONNECTION_POINTS_H__
#define __C_[UPPER_PROJECT_NAME]_ENUM_CONNECTION_POINTS_H__

#include "IEcoSystem1.h"
#include "IEcoEnumConnectionPoints.h"
#include "IdEcoList1.h"
#include "IdEcoMemoryManager1.h"

typedef struct C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints* C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPointsPtr_t;

typedef struct C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints {

    IEcoEnumConnectionPointsVTbl* m_pVTblIECP;

    int16_t (ECOCALLMETHOD *Init)(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPointsPtr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ struct IEcoConnectionPoint *pCP);
    int16_t (ECOCALLMETHOD *Create)(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPointsPtr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem);
    void (ECOCALLMETHOD *Delete)(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPointsPtr_t pCMe);

    IEcoList1* m_List;
    IEcoMemoryAllocator1* m_pIMem;
    IEcoSystem1* m_pISys;

} C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints;

#endif /* __C_[UPPER_PROJECT_NAME]_ENUM_CONNECTION_POINTS_H__ */

## Шаблон EnumConnectionPoints (Source)
#include "IEcoSystem1.h"
#include "IEcoInterfaceBus1.h"
#include "IEcoInterfaceBus1MemExt.h"
#include "C[FIX_PROJECT_NAME]EnumConnectionPoints.h"

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints_QueryInterface(/* in */ IEcoEnumConnectionPointsPtr_t me, /* in */ const UGUID* riid, /* out */ void** ppv) {
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

static uint32_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints_AddRef(/* in */ IEcoEnumConnectionPointsPtr_t me) {
    return 0;
}

static uint32_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints_Release(/* in */ IEcoEnumConnectionPointsPtr_t me) {
    return 0;
}

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints_Next(/* in */ IEcoEnumConnectionPointsPtr_t me, /* in */ uint32_t cConnections, /* out */ struct IEcoConnectionPoint **ppCP, /* out */ uint32_t *pcFetched) {
    return -1;
}

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints_Skip(/* in */ IEcoEnumConnectionPointsPtr_t me, /* in */ uint32_t cConnections) {
    return -1;
}

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints_Reset(/* in */ IEcoEnumConnectionPointsPtr_t me) {
    return 0 ;
}

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints_Clone(/* in */ IEcoEnumConnectionPointsPtr_t me, /* out */ struct IEcoEnumConnectionPoints **ppEnum) {
    return 0;
}

static int16_t ECOCALLMETHOD initC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPointsPtr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ struct IEcoConnectionPoint *pCP) {
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

static int16_t ECOCALLMETHOD createC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPointsPtr_t pCMe, /* in */ IEcoUnknown* pIUnkSystem) {
     int16_t result = ERR_ECO_POINTER;

    /* Pointer Validation */
    if (pCMe == 0) {
        return result; /* ERR_ECO_POINTER */
    }


    return ERR_ECO_SUCCESES;
}

static void ECOCALLMETHOD deleteC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPointsPtr_t pCMe) {
 
    if (pCMe != 0 ) {
        if (pCMe->m_List != 0) {
            pCMe->m_List->pVTbl->Clear(pCMe->m_List);
            pCMe->m_List->pVTbl->Release(pCMe->m_List);
        }

    }
}

/* Create Virtual Table IEcoEnumConnectionPointsVTbl */
IEcoEnumConnectionPointsVTbl g_x0000000400000000C000000000000046VTblECP[GUID_CID_NAMESPACE] = {
	C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints_QueryInterface,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints_AddRef,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints_Release,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints_Next,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints_Skip,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints_Reset,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints_Clone	
};

/* Object Instance */
C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints g_xC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints = {
    &g_x0000000400000000C000000000000046VTblECP[GUID_CID_NAMESPACE],
    initC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints,
    createC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints,
    deleteC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionPoints,
    0, /* m_pList */
    0, /* m_pIMem */
    0 /* m_pISys */  
};

# ECO CONNECTIONS (Enumerator)
При реализации перечислителя активных подключений (Sinks) используй заголовочный файл `HeaderFiles/CEco[Name]EnumConnections.h`:

## Шаблон EnumConnections (Header)
#ifndef __C_[UPPER_PROJECT_NAME]_ENUM_CONNECTIONS_H__
#define __C_[UPPER_PROJECT_NAME]_ENUM_CONNECTIONS_H__

#include "IEcoEnumConnections.h"
#include "IdEcoList1.h"
#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"

typedef struct C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections* C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionsPtr_t;

typedef struct C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections {

    IEcoEnumConnectionsVTbl* m_pVTblIEC;

    int16_t (ECOCALLMETHOD *Init)(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionsPtr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoList1* pIList);
    int16_t (ECOCALLMETHOD *Create)(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionsPtr_t pCMe, /* in */ IEcoUnknownPtr_t pIUnkSystem);
    void (ECOCALLMETHOD *Delete)(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionsPtr_t pCMe);

    uint32_t m_cRef;
    IEcoList1* m_pSinkList;
    uint32_t m_cIndex;
    IEcoMemoryAllocator1* m_pIMem;
    IEcoSystem1* m_pISys;

} C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections;

#endif /* __C_[UPPER_PROJECT_NAME]_ENUM_CONNECTIONS_H__ */


## Шаблон EnumConnections (Source)
#include "IEcoInterfaceBus1.h"
#include "IEcoInterfaceBus1MemExt.h"
#include "C[FIX_PROJECT_NAME]EnumConnections.h"

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections_QueryInterface(/* in */ IEcoEnumConnectionsPtr_t me, /* in */ const UGUID* riid, /* out */ void** ppv) {
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

static uint32_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections_AddRef(/* in */ IEcoEnumConnectionsPtr_t me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections*)me;

    if (me == 0 ) {
        return -1;
    }

    return ++pCMe->m_cRef;
}

static uint32_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections_Release(/* in */ IEcoEnumConnectionsPtr_t me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections*)me;

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

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections_Next(/* in */ IEcoEnumConnectionsPtr_t me, /* in */ uint32_t cConnections, /* out */ struct EcoConnectionData *rgcd, /* out */ uint32_t *pcFetched) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections*)me;
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

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections_Skip(/* in */ IEcoEnumConnectionsPtr_t me, /* in */ uint32_t cConnections) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections*)me;
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

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections_Reset(/* in */ IEcoEnumConnectionsPtr_t me) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections*)me;

    if (me == 0 ) {
        return -1;
    }

    pCMe->m_cIndex = 0;

    return 0;
}

static int16_t ECOCALLMETHOD C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections_Clone(/* in */ IEcoEnumConnectionsPtr_t me, /* out */ struct IEcoEnumConnections **ppEnum) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections*)me;
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections* pCObj = 0;
    int16_t result = ERR_ECO_POINTER;

    if (me == 0 || ppEnum ==0 ) {
        return result;
    }

    pCObj = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections*)pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, sizeof(C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections));
    pCObj = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections*)pCMe->m_pIMem->pVTbl->Copy(pCMe->m_pIMem, pCObj, pCMe, sizeof(C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections));
    pCObj->Create(pCObj, (IEcoUnknownPtr_t)pCMe->m_pISys);
    result = pCObj->Init(pCObj, (IEcoUnknownPtr_t)pCMe->m_pISys, pCMe->m_pSinkList);
    *ppEnum = (IEcoEnumConnectionsPtr_t)pCObj;

    return result;
}

static int16_t ECOCALLMETHOD initC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections(/*in*/ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnectionsPtr_t me, /* in */ IEcoUnknownPtr_t pIUnkSystem, /* in */ IEcoList1* pIList) {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections* pCMe = (C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections*)me;
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

static int16_t ECOCALLMETHOD createC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections(/* in */ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections* pCMe, /* in */ IEcoUnknown* pIUnkSystem) {
    int16_t result = ERR_ECO_POINTER;

    /* Pointer Validation */
    if (pCMe == 0) {
        return result; /* ERR_ECO_POINTER */
    }


    return ERR_ECO_SUCCESES;
}

static void ECOCALLMETHOD deleteC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections(/* in */ C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections* pCMe) {
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
IEcoEnumConnectionsVTbl g_x0000000200000000C000000000000046VTblECP[GUID_CID_NAMESPACE] = {
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections_QueryInterface,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections_AddRef,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections_Release,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections_Next,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections_Skip,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections_Reset,
    C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections_Clone	
};

/* Object Instance */
C[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections g_xC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections = {
    &g_x0000000200000000C000000000000046VTblECP[GUID_CID_NAMESPACE],
    initC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections,
    createC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections,
    deleteC[FIX_PROJECT_NAME][GUID_CID_NAMESPACE]EnumConnections,
    1, /* m_cRef */
    0, /* m_pSinkList */
    0, /* m_cIndex */
    0, /* m_pIMem */  
    0  /* m_pISys */
};


# ECO EVENT SINK (Client Side)
При создании объекта для приема событий в юнит-тестах (`UnitTestFiles/HeaderFiles/CEco[Name]Sink.h`) используй этот шаблон:

## Шаблон Sink-объекта (Header)

#ifndef __C_[UPPER_PROJECT_NAME]_SINK_H__
#define __C_[UPPER_PROJECT_NAME]_SINK_H__

#include "I[!output FIX_PROJECT_NAME].h"
#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"

typedef struct C[!output FIX_PROJECT_NAME]Sink {

    /* Таблица функций интерфейса I[!output FIX_PROJECT_NAME]Events */
    I[!output FIX_PROJECT_NAME]VTblEvents* m_pVTblI[!output FIX_PROJECT_NAME]Events;

    /* Вспомогательные функции */
    int16_t (ECOCALLMETHOD *Advise)(/* in */ struct C[!output FIX_PROJECT_NAME]Sink* me, /* in */I[!output FIX_PROJECT_NAME] *pI[!output FIX_PROJECT_NAME]);
    int16_t (ECOCALLMETHOD *Unadvise)(/* in */ struct C[!output FIX_PROJECT_NAME]Sink* me, /* in */I[!output FIX_PROJECT_NAME] *pI[!output FIX_PROJECT_NAME]);

    /* Счетчик ссылок */
    uint32_t m_cRef;
    uint32_t m_cCookie;

    /* Интерфейс для работы с памятью */
    IEcoMemoryAllocator1* m_pIMem;


} C[!output FIX_PROJECT_NAME]Sink, *C[!output FIX_PROJECT_NAME]SinkPtr;

/* Создание экземпляра */
int16_t ECOCALLMETHOD createC[!output FIX_PROJECT_NAME]Sink(/* in */ IEcoMemoryAllocator1* pIMem, /* out */ I[!output FIX_PROJECT_NAME]Events** ppI[!output FIX_PROJECT_NAME]Events);
/* Удаление */
void ECOCALLMETHOD deleteC[!output FIX_PROJECT_NAME]Sink(/* in */ I[!output FIX_PROJECT_NAME]Events* pI[!output FIX_PROJECT_NAME]Events);

#endif /* __C_[UPPER_PROJECT_NAME]_SINK_H__ */

## Шаблон Sink-объекта (Source)
#include "C[!output FIX_PROJECT_NAME]Sink.h"
#include "IEcoConnectionPointContainer.h"

int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Sink_QueryInterface(/* in */ struct I[!output FIX_PROJECT_NAME]Events* me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    if ( IsEqualUGUID(riid, &IID_I[!output FIX_PROJECT_NAME]Events ) ) {
        *ppv = me;
        me->pVTbl->AddRef(me);
        return 0;
    }
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown ) ) {
        *ppv = me;
        me->pVTbl->AddRef(me);
        return 0;
    }

    *ppv = 0;

    return -1;
}

uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Sink_AddRef(/* in */ struct I[!output FIX_PROJECT_NAME]Events* me) {
    C[!output FIX_PROJECT_NAME]Sink* pCMe = (C[!output FIX_PROJECT_NAME]Sink*)me;

    if (me == 0 ) {
        return -1;
    }

    pCMe->m_cRef++;
    return pCMe->m_cRef;
}

uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Sink_Release(/* in */ struct I[!output FIX_PROJECT_NAME]Events* me) {
    C[!output FIX_PROJECT_NAME]Sink* pCMe = (C[!output FIX_PROJECT_NAME]Sink*)me;

    if (me == 0 ) {
        return -1;
    }

    /* Уменьшение счетчика ссылок на компонент */
    --pCMe->m_cRef;

    /* В случае обнуления счетчика, освобождение данных экземпляра */
    if ( pCMe->m_cRef == 0 ) {
        deleteC[!output FIX_PROJECT_NAME]Sink((I[!output FIX_PROJECT_NAME]Events*)pCMe);
        return 0;
    }
    return pCMe->m_cRef;
}

int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Sink_OnMyCallback(/* in */ struct I[!output FIX_PROJECT_NAME]Events* me, /* in */ char_t* Name) {
    C[!output FIX_PROJECT_NAME]Sink* pCMe = (C[!output FIX_PROJECT_NAME]Sink*)me;

    if (me == 0 ) {
        return -1;
    }


    return 0;
}

int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Sink_Advise(/* in */ struct C[!output FIX_PROJECT_NAME]Sink* me, /* in */I[!output FIX_PROJECT_NAME] *pI[!output FIX_PROJECT_NAME]) {
    IEcoConnectionPointContainer* pCPC = 0;
    IEcoConnectionPoint* pCP = 0;
    int16_t result = 0;

    result = pI[!output FIX_PROJECT_NAME]->pVTbl->QueryInterface(pI[!output FIX_PROJECT_NAME], &IID_IEcoConnectionPointContainer, (void**)&pCPC);

    if (result == 0 && pCPC != 0) {
        result = pCPC->pVTbl->FindConnectionPoint(pCPC, &IID_I[!output FIX_PROJECT_NAME]Events, &pCP);
        pCPC->pVTbl->Release(pCPC);
        pCPC = 0;
        if (result == 0 && pCP != 0) {

            result = pCP->pVTbl->Advise(pCP, (IEcoUnknown*)me, &me->m_cCookie);
            pCP->pVTbl->Release(pCP);
            pCP = 0;
        }
    }

    return result;
}

int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Sink_Unadvise(/* in */ struct C[!output FIX_PROJECT_NAME]Sink* me, /* in */I[!output FIX_PROJECT_NAME] *pI[!output FIX_PROJECT_NAME]) {
    IEcoConnectionPointContainer* pCPC = 0;
    IEcoConnectionPoint * pCP = 0;
    int16_t result = 0;

    if (me->m_cCookie) {
        result = pI[!output FIX_PROJECT_NAME]->pVTbl->QueryInterface(pI[!output FIX_PROJECT_NAME], &IID_IEcoConnectionPointContainer, (void**)&pCPC);
        if (result == 0) {
            result = pCPC->pVTbl->FindConnectionPoint(pCPC, &IID_I[!output FIX_PROJECT_NAME]Events, &pCP);
            pCPC->pVTbl->Release(pCPC);
            pCPC = 0;
            if (result == 0) {
                result = pCP->pVTbl->Unadvise(pCP, me->m_cCookie);
                pCP->pVTbl->Release(pCP);
                pCP = 0;
            }
        }
    }
    return result;
}

/* Create Virtual Table I[!output FIX_PROJECT_NAME]VTblEvents */
I[!output FIX_PROJECT_NAME]VTblEvents g_x[!output GUID_IID_TARGET]VTblEvents = {
    C[!output FIX_PROJECT_NAME]Sink_QueryInterface,
    C[!output FIX_PROJECT_NAME]Sink_AddRef,
    C[!output FIX_PROJECT_NAME]Sink_Release,
    C[!output FIX_PROJECT_NAME]Sink_OnMyCallback
};

int16_t ECOCALLMETHOD createC[!output FIX_PROJECT_NAME]Sink(/* in */ IEcoMemoryAllocator1* pIMem, /* out */ I[!output FIX_PROJECT_NAME]Events** ppI[!output FIX_PROJECT_NAME]Events) {
    int16_t result = -1;
    C[!output FIX_PROJECT_NAME]Sink* pCMe = 0;

    /* Проверка указателей */
    if (ppI[!output FIX_PROJECT_NAME]Events == 0 || pIMem == 0 ) {
        return result;
    }

    /* Выделение памяти для данных экземпляра */
    pCMe = (C[!output FIX_PROJECT_NAME]Sink*)pIMem->pVTbl->Alloc(pIMem, sizeof(C[!output FIX_PROJECT_NAME]Sink));

    /* Сохранение указателя на интерфейс для работы с памятью */
    pCMe->m_pIMem = pIMem;
    pCMe->m_pIMem->pVTbl->AddRef(pCMe->m_pIMem);

    /* Установка счетчика ссылок на компонент */
    pCMe->m_cRef = 1;

    /* Создание таблицы функций интерфейса IEcoP2PEvents */
    pCMe->m_pVTblI[!output FIX_PROJECT_NAME]Events = &g_x[!output GUID_IID_TARGET]VTblEvents;

    *ppI[!output FIX_PROJECT_NAME]Events = (I[!output FIX_PROJECT_NAME]Events*)pCMe;

    return 0;
};

void ECOCALLMETHOD deleteC[!output FIX_PROJECT_NAME]Sink(I[!output FIX_PROJECT_NAME]Events* pI[!output FIX_PROJECT_NAME]Events) {
    C[!output FIX_PROJECT_NAME]Sink* pCMe = (C[!output FIX_PROJECT_NAME]Sink*)pI[!output FIX_PROJECT_NAME]Events;
    IEcoMemoryAllocator1* pIMem = 0;

    if (pI[!output FIX_PROJECT_NAME]Events != 0 ) {
        pIMem = pCMe->m_pIMem;
        /* Освобождение */
        pIMem->pVTbl->Free(pIMem, pCMe);
        pIMem->pVTbl->Release(pIMem);
    }
};
