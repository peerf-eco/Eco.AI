/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   C[!output FIX_PROJECT_NAME]
 * </summary>
 *
 * <description>
 *   This source code describes the implementation of the interfaces for C[!output FIX_PROJECT_NAME]
 * </description>
 *
 * <author>
 *   Copyright (c) 2026 [!output AUTHOR]. All rights reserved.
 * </author>
 *
 */

#include "IEcoSystem1.hpp"
#include "IEcoInterfaceBus1.hpp"
#include "IEcoInterfaceBus1MemExt.hpp"
#include "C[!output FIX_PROJECT_NAME].hpp"
[!if ADD_CONNECTION_POINTS]
#include "C[!output FIX_PROJECT_NAME]EnumConnectionPoints.hpp"
#include "IEcoConnectionPointContainer.hpp"
[!endif]

[!if ADD_POSTFIX_NAMESPACE]
namespace [!output GUID_CID_NAMESPACE]
{
[!endif]	
/*
 *
 * <сводка>
 *   Функция QueryInterface
 * </сводка>
 *
 * <описание>
 *   Функция QueryInterface для интерфейса I[!output FIX_PROJECT_NAME]
 * </описание>
 *
 */
int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]::QueryInterface(/* in */ const UGUID* riid, /* out */ void** ppv) {

[!if ADD_AGGREGATION_INNER]
    return m_pIUnkOuter->QueryInterface(riid, ppv);
[!else]
    /* Проверка и получение запрошенного интерфейса */
    if ( IsEqualUGUID(riid, &IID_I[!output FIX_PROJECT_NAME]) ) {
        *ppv = static_cast<I[!output FIX_PROJECT_NAME]*>(this);
        reinterpret_cast<IEcoUnknown*>(*ppv)->AddRef();
    }
[!if ADD_CONTAINMENT_OUTER]
    else if (IsEqualUGUID(riid, &IID_IEcoXXX)) {
        *ppv = static_cast<IEcoUnknown*>(this);
        reinterpret_cast<IEcoUnknown*>(*ppv)->AddRef();
    }
[!endif]	
[!if ADD_CONNECTION_POINTS]
    else if ( IsEqualUGUID(riid, &IID_IEcoConnectionPointContainer) ) {
        *ppv = &pCMe->m_pVTblICPC;
        reinterpret_cast<IEcoUnknown*>(*ppv)->AddRef();
    }
[!endif]
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown) ) {
        *ppv = static_cast<IEcoUnknown*>(this);
        reinterpret_cast<IEcoUnknown*>(*ppv)->AddRef();
    }
[!if ADD_AGGREGATION_OUTER]
    /* Слепое агрегирование */
    else if (m_pIUnkInner != 0) {
        /* Запрашиваем интерфейс внутреннего компонента */
        return m_pIUnkInner->QueryInterface(riid, ppv);
    }
[!endif]
    else {
        *ppv = 0;
        return (int16_t)ERR_ECO_NOINTERFACE;
    }
    return (int16_t)ERR_ECO_SUCCESES;
[!endif]
}

/*
 *
 * <сводка>
 *   Функция AddRef
 * </сводка>
 *
 * <описание>
 *   Функция AddRef для интерфейса I[!output FIX_PROJECT_NAME]
 * </описание>
 *
 */
uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]::AddRef() {
[!if ADD_AGGREGATION_INNER]
    return m_pIUnkOuter->AddRef();
[!else]
[!if THREAD_SAFE]
    return atomicincrement_int32_t(reinterpret_cast<volatile long*>(&m_cRef));
[!else]
    return ++m_cRef;
[!endif]
[!endif]
}

/*
 *
 * <сводка>
 *   Функция Release
 * </сводка>
 *
 * <описание>
 *   Функция Release для интерфейса I[!output FIX_PROJECT_NAME]
 * </описание>
 *
 */
uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]::Release() {
[!if ADD_AGGREGATION_INNER]
    return m_pIUnkOuter->Release();
[!else]
    /* Уменьшение счетчика ссылок на компонент */
[!if THREAD_SAFE]
    atomicdecrement_int32_t(reinterpret_cast<volatile long*>(&m_cRef));
[!else]
    --m_cRef;
[!endif]

    /* В случае обнуления счетчика, освобождение данных экземпляра */
    if ( m_cRef == 0 ) {
[!if ADD_AGGREGATION_OUTER]
        if ( m_pIUnkInner != 0 ) {
            /* Предотвращение рекурсивного вызова */
            if (m_pIUnkInner->Release() == 0) {
                m_pIUnkInner = 0;
            }
            else {
                m_cRef = 1;
            }
        }
        if ( m_cRef == 0 ) {
			delete this;
        }		
[!else]
        delete this;
[!endif]		
        return 0;
    }
    return m_cRef;
[!endif]
}

/*
 *
 * <сводка>
 *   Функция MyFunction
 * </сводка>
 *
 * <описание>
 *   Функция
 * </описание>
 *
 */
int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]::MyFunction(/* in */ char_t* Name, /* out */ char_t** copyName) {
    int16_t index = 0;

    /* Проверка указателей */
    if (Name == 0 || copyName == 0) {
        return (int16_t)ERR_ECO_POINTER;
    }

    /* Копирование строки */
    while(Name[index] != 0) {
        index++;
    }
    m_Name = (char_t*)m_pIMem->Alloc(index + 1);
    index = 0;
    while(Name[index] != 0) {
        m_Name[index] = Name[index];
        index++;
    }
    *copyName = m_Name;

[!if ADD_CONNECTION_POINTS]
    /* Обратный вызов */
    Fire_OnMyCallback(m_Name);

[!endif]
    return ERR_ECO_SUCCESES;
}

[!if ADD_AGGREGATION_INNER]
/*
 *
 * <сводка>
 *   Функция NondelegatingQueryInterface
 * </сводка>
 *
 * <описание>
 *   Функция NondelegatingQueryInterface для интерфейса I[!output FIX_PROJECT_NAME]
 * </описание>
 *
 */
int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]::NondelegatingQueryInterface(/* in */ const UGUID* riid, /* out */ void** ppv) {

    /* Проверка указателей */
    if (ppv == 0) {
        return (int16_t)ERR_ECO_POINTER;
    }

    /* Проверка и получение запрошенного интерфейса */
    if ( IsEqualUGUID(riid, &IID_I[!output FIX_PROJECT_NAME]) ) {
        *ppv = &pCMe->m_pVTblI[!output FIX_PROJECT_NAME];
        pCMe->m_pVTblI[!output FIX_PROJECT_NAME]->AddRef((I[!output FIX_PROJECT_NAME]*)pCMe);
    }
[!if ADD_CONNECTION_POINTS]
    else if ( IsEqualUGUID(riid, &IID_IEcoConnectionPointContainer) ) {
        *ppv = &pCMe->m_VtblICPC;
        pCMe->m_pVTblICPC->AddRef((I[!output FIX_PROJECT_NAME]*)pCMe);
    }
[!endif]
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown) ) {
        *ppv = &pCMe->m_pVTblI[!output FIX_PROJECT_NAME];
        pCMe->m_pVTblI[!output FIX_PROJECT_NAME]->AddRef((I[!output FIX_PROJECT_NAME]*)pCMe);
    }
    else {
        *ppv = 0;
        return (int16_t)ERR_ECO_NOINTERFACE;
    }
    return (int16_t)ERR_ECO_SUCCESES;
}

/*
 *
 * <сводка>
 *   Функция NondelegatingAddRef
 * </сводка>
 *
 * <описание>
 *   Функция NondelegatingAddRef для интерфейса I[!output FIX_PROJECT_NAME]
 * </описание>
 *
 */
uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]::NondelegatingAddRef() {
    return ++m_cRef;
}

/*
 *
 * <сводка>
 *   Функция NondelegatingRelease
 * </сводка>
 *
 * <описание>
 *   Функция NondelegatingRelease для интерфейса I[!output FIX_PROJECT_NAME]
 * </описание>
 *
 */
uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]::NondelegatingRelease() {
    /* Уменьшение счетчика ссылок на компонент */
    --m_cRef;

    /* В случае обнуления счетчика, освобождение данных экземпляра */
    if (m_cRef == 0 ) {
        delete this;
        return 0;
    }
    return m_cRef;
}
[!endif]

[!if ADD_CONTAINMENT_OUTER]
/*
 *
 * <сводка>
 *   Функция QueryInterface
 * </сводка>
 *
 * <описание>
 *   Функция QueryInterface для интерфейса IEcoXXXX
 * </описание>
 *
 */
int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]_IEcoXXXX_QueryInterface(/* in */ const UGUID* riid, /* out */ void** ppv) {

    /* Проверка указателей */
    if ( ppv == 0) {
        return (int16_t)ERR_ECO_POINTER;
    }

    /* Проверка и получение запрошенного интерфейса */
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
        pCMe->m_pVTblICPC->AddRef((I[!output FIX_PROJECT_NAME]*)pCMe);
    }
[!endif]
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown) ) {
        *ppv = &pCMe->m_pVTblI[!output FIX_PROJECT_NAME];
        pCMe->m_pVTblI[!output FIX_PROJECT_NAME]->AddRef((I[!output FIX_PROJECT_NAME]*)pCMe);
    }
    else {
        *ppv = 0;
        return (int16_t)ERR_ECO_NOINTERFACE;
    }
    return (int16_t)ERR_ECO_SUCCESES;
}

/*
 *
 * <сводка>
 *   Функция AddRef
 * </сводка>
 *
 * <описание>
 *   Функция AddRef для интерфейса IEcoXXXX
 * </описание>
 *
 */
uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]_IEcoXXXX_AddRef() {
    return ++m_cRef;
}

/*
 *
 * <сводка>
 *   Функция Release
 * </сводка>
 *
 * <описание>
 *   Функция Release для интерфейса IEcoXXXX
 * </описание>
 *
 */
uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]_IEcoXXXX_Release() {
    /* Уменьшение счетчика ссылок на компонент */
    --m_cRef;

    /* В случае обнуления счетчика, освобождение данных экземпляра */
    if ( m_cRef == 0 ) {
        delete this;
        return 0;
    }
    return m_cRef;
}
[!endif]

[!if ADD_CONNECTION_POINTS]
/*
 *
 * <сводка>
 *   Функция QueryInterface
 * </сводка>
 *
 * <описание>
 *   Функция QueryInterface для интерфейса IEcoConnectionPointContainer
 * </описание>
 *
 */
int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]_IEcoConnectionPointContainer_QueryInterface(/* in */ const UGUID* riid, /* out */ void** ppv) {
    if (ppv == 0) {
        return (int16_t)ERR_ECO_POINTER;
    }

    /* Проверка и получение запрошенного интерфейса */
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
 * <сводка>
 *   Функция AddRef
 * </сводка>
 *
 * <описание>
 *   Функция AddRef для интерфейса IEcoConnectionPointContainer
 * </описание>
 *
 */
uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]_IEcoConnectionPointContainer_AddRef() {
    return ++m_cRef;
}

/*
 *
 * <сводка>
 *   Функция Release
 * </сводка>
 *
 * <описание>
 *   Функция Release для интерфейса IEcoConnectionPointContainer
 * </описание>
 *
 */
uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]_IEcoConnectionPointContainer_Release() {

    /* Уменьшение счетчика ссылок на компонент */
    --m_cRef;

    /* В случае обнуления счетчика, освобождение данных экземпляра */
    if (m_cRef == 0 ) {
        delete this;
        return 0;
    }
    return m_cRef;
}

/*
 *
 * <сводка>
 *   Функция EnumConnectionPoints
 * </сводка>
 *
 * <описание>
 *   Функция
 * </описание>
 *
 */
int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]_IEcoConnectionPointContainer_EnumConnectionPoints(/* out */ struct IEcoEnumConnectionPoints **ppEnum) {
    if (ppEnum == 0 ) {
        return result;
    }

    //result = createC[!output FIX_PROJECT_NAME]EnumConnectionPoints[!output GUID_CID_NAMESPACE]((IEcoUnknown*)pCMe->m_pISys, &pCMe->m_pISinkCP->m_pVTblICP, ppEnum);

    return result;
}

/*
 *
 * <сводка>
 *   Функция FindConnectionPoint
 * </сводка>
 *
 * <описание>
 *   Функция
 * </описание>
 *
 */
int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]_IEcoConnectionPointContainer_FindConnectionPoint(/* in */ const UGUID* riid, /* out */ struct IEcoConnectionPoint **ppCP) {
    int16_t result = (int16_t)ERR_ECO_POINTER;

    if (ppCP == 0 ) {
        return result;
    }

    if ( !IsEqualUGUID(riid, &IID_I[!output FIX_PROJECT_NAME]Events ) ) {
        *ppCP = 0;
        return (int16_t)ERR_ECO_OUTINTERFACE_NOCONNECTION;
    }

    if (pCMe->m_pISinkCP == 0) {
        return (int16_t)ERR_ECO_FAIL;
    }

    pCMe->m_pISinkCP->m_pVTblICP->AddRef(&pCMe->m_pISinkCP->m_pVTblICP);
    *ppCP =  &m_pISinkCP->m_pVTblICP;

    return (int16_t)ERR_ECO_SUCCESES;
}

/*
 *
 * <сводка>
 *   Функция Fire_OnSearchStarted
 * </сводка>
 *
 * <описание>
 *   Функция вызова обратного интерфейса
 * </описание>
 *
 */
int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]_I[!output FIX_PROJECT_NAME]Events_Fire_OnMyCallback(/* in */ struct C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* me, /* in */ char_t* Name) {
    C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]* pCMe = (C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]*)me;
    int16_t result = (int16_t)ERR_ECO_POINTER;
    uint32_t count = 0;
    uint32_t index = 0;
    IEcoEnumConnections* pEnum = 0;
    I[!output FIX_PROJECT_NAME]Events* pIEvents = 0;
    EcoConnectionData cd;

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
 * <сводка>
 *   Функция Init
 * </сводка>
 *
 * <описание>
 *   Функция инициализации экземпляра
 * </описание>
 *
 */
int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]::Init(/* in */ IEcoUnknown* pIUnkSystem) {
    IEcoInterfaceBus1* pIBus = 0;
[!if ADD_AGGREGATION_OUTER]
    IEcoUnknown* pOuterUnknown = (IEcoUnknown*)me;
[!endif]
    IEcoInterfaceBus1MemExt* pIMemExt = 0;
    int16_t result = (int16_t)ERR_ECO_POINTER;
    UGUID* rcid = (UGUID*)&CID_EcoMemoryManager1;	

    /* Проверка указателей */
    if (pIUnkSystem == 0 ) {
        return result;
    }

    /* Сохранение указателя на системный интерфейс */
    m_pISys = (IEcoSystem1*)pIUnkSystem;


    /* Получение системного интерфейса приложения */
    result = pIUnkSystem->QueryInterface(&GID_IEcoSystem, (void **)&m_pISys);
    /* Проверка */
    if (result != 0 || m_pISys == 0) {
        return (int16_t)ERR_ECO_NOSYSTEM;
    }

    /* Получение интерфейса для работы с интерфейсной шиной */
    result = m_pISys->QueryInterface(&IID_IEcoInterfaceBus1, (void **)&pIBus);
    /* Проверка */
    if (result != 0 || pIBus == 0) {
        m_pISys->Release();
        return (int16_t)ERR_ECO_NOBUS;
    }

    /* Получение идентификатора компонента для работы с памятью */
    result = pIBus->QueryInterface(&IID_IEcoInterfaceBus1MemExt, (void**)&pIMemExt);
    if (result == 0 && pIMemExt != 0) {
        rcid = (UGUID*)pIMemExt->get_Manager();
        pIMemExt->Release();
    }

    /* Получение интерфейса распределителя памяти */
    result = pIBus->QueryComponent(rcid, 0, &IID_IEcoMemoryAllocator1, (void**) &m_pIMem);
    /* Проверка */
    if (result != 0 || m_pIMem == 0) {
        /* Освобождение в случае ошибки */
        pIBus->Release();
        m_pISys->Release();
        return (int16_t)ERR_ECO_GET_MEMORY_ALLOCATOR;
    }

[!if ADD_CONNECTION_POINTS]
    /* Создание точки подключения */
    result = createC[!output FIX_PROJECT_NAME]ConnectionPoint[!output GUID_CID_NAMESPACE]((IEcoUnknown*)pCMe->m_pISys, &pCMe->m_pVTblICPC, &IID_I[!output FIX_PROJECT_NAME]Events, (IEcoConnectionPoint**)&((pCMe)->m_pISinkCP));
    if (result == 0 && pCMe->m_pISinkCP != 0) {
        result = (int16_t)ERR_ECO_SUCCESES;
    }

[!endif]

[!if ADD_AGGREGATION_OUTER]
    /* Создание внутреннего компонента c поддержкой агрегирования */
    /* ВАЖНО: При агрегировании мы передаем IID IEcoUnknown */
    result = pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoXXXX, pOuterUnknown, &IID_IEcoUnknown, (void**) &pCMe->m_pIUnkInner);
[!endif]
[!if ADD_CONTAINMENT_OUTER]
    /* Создание внутреннего компонента (включение) */
    /*result = pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoXXXX, 0, &IID_IEcoXXXX, (void**) &pCMe->m_pIXXXX);*/
[!endif]

    /* Инициализация данных */
    m_Name = 0;

    /* Освобождение */
    pIBus->Release();
	
    return result;
}

/*
 *
 * <сводка>
 *   Функция Create
 * </сводка>
 *
 * <описание>
 *   Функция создания экземпляра
 * </описание>
 *
 */
C[!output FIX_PROJECT_NAME]::C[!output FIX_PROJECT_NAME](/* in */ IEcoUnknown* pIUnkSystem, /* in */ IEcoUnknown* pIUnkOuter) :
    m_cRef(1),
    m_pIMem(0),
    m_pISys(0),
    m_Name(0)
{
}

/*
 *
 * <сводка>
 *   Функция Delete
 * </сводка>
 *
 * <описание>
 *   Функция освобождения экземпляра
 * </описание>
 *
 */
C[!output FIX_PROJECT_NAME]::~C[!output FIX_PROJECT_NAME]() {
    /* Освобождение */
    if ( m_Name != 0 && m_pIMem != 0 ) {
        m_pIMem->Free(m_Name);
    }
[!if ADD_CONNECTION_POINTS]
    if (pCMe->m_pISinkCP != 0) {
        deleteC[!output FIX_PROJECT_NAME]ConnectionPoint[!output GUID_CID_NAMESPACE]((IEcoConnectionPoint*)(pCMe->m_pISinkCP));
        m_pISinkCP = 0;
    }
[!endif]
    if ( m_pISys != 0 ) {
        m_pISys->Release();
    }
    if ( m_pIMem != 0 ) {
        m_pIMem->Release();
    }
}

[!if ADD_POSTFIX_NAMESPACE]
} /* namespace [!output GUID_CID_NAMESPACE] */
[!endif]