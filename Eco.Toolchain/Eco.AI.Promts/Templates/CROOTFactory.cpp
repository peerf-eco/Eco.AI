/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   C[!output FIX_PROJECT_NAME]Factory
 * </summary>
 *
 * <description>
 *   This header describes the implementation of the factory for the component
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
#include "C[!output FIX_PROJECT_NAME]Factory.hpp"

[!if ADD_POSTFIX_NAMESPACE]
namespace [!output GUID_CID_NAMESPACE]
{
[!endif]		
/*
 *
 * <summary>
 *   QueryInterface function
 * </summary>
 *
 * <description>
 *   The function returns a pointer to the interface
 * </description>
 *
 */
int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Factory::QueryInterface(const UGUID* riid, void** ppv) {
    if ( IsEqualUGUID(riid, &IID_IEcoUnknown) || IsEqualUGUID(riid, &IID_IEcoComponentFactory) ) {
        *ppv = static_cast<IEcoComponentFactory*>(this);
    }
    else {
        *ppv = 0;
        return (int16_t)ERR_ECO_NOINTERFACE;
    }
    reinterpret_cast<IEcoUnknown*>(*ppv)->AddRef();

    return (int16_t)ERR_ECO_SUCCESES;
}

/*
 *
 * <summary>
 *   AddRef function
 * </summary>
 *
 * <description>
 *   The function increments the reference count for the interface
 * </description>
 *
 */
uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Factory::AddRef() {
[!if THREAD_SAFE]
    return atomicincrement_int32_t(reinterpret_cast<volatile long*>(&m_cRef));
[!else]
    return ++m_cRef;
[!endif]
}

/*
 *
 * <summary>
 *   Release function
 * </summary>
 *
 * <description>
 *   The function decrements the reference count for the interface
 * </description>
 *
 */
uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Factory::Release() {

    /* Decrementing the component reference counter */
[!if THREAD_SAFE]
    atomicdecrement_int32_t(reinterpret_cast<volatile long*>(&m_cRef));
[!else]
    --m_cRef;
[!endif]

    /* If the counter reaches zero, free the instance data */
    if ( m_cRef == 0 ) {
        return 0;
    }
    return m_cRef;
}

/*
 *
 * <summary>
 *   Init function
 * </summary>
 *
 * <description>
 *   The function initializes the component with parameters
 * </description>
 *
 */
int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Factory::Init(/* in */ IEcoUnknown *pIUnkSystem, /* in */ void* pv) {
    int16_t result = (int16_t)ERR_ECO_POINTER;

    /* Initializing the component with parameters */

    return result;
}

/*
 *
 * <summary>
 *   Alloc function
 * </summary>
 *
 * <description>
 *   The function creates a component
 * </description>
 *
 */
int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Factory::Alloc(/* in */ IEcoUnknown *pISystem, /* in */ IEcoUnknown *pIUnknownOuter, /* in */ const UGUID* riid, /* out */ void** ppv) {
    int16_t result = (int16_t)ERR_ECO_POINTER;
    IEcoSystem1* pISys = 0;
    IEcoInterfaceBus1* pIBus = 0;
    IEcoInterfaceBus1MemExt* pIMemExt = 0;
    IEcoMemoryAllocator1* pIMem = 0;
    C[!output FIX_PROJECT_NAME]* pCObj = 0;
    UGUID* rcid = (UGUID*)&CID_EcoMemoryManager1;

    if (pISystem == 0 ) {
        return result; /* ERR_ECO_POINTER */
    }

    /* Aggregation provided the IID is IID_IEcoUnknown */
    if ( ( pIUnknownOuter != 0 ) && !IsEqualUGUID(riid, &IID_IEcoUnknown ) ) {
        /* aggregation not supported */
        return (int16_t)ERR_ECO_NOAGGREGATION;
    }

    /* Getting the application system interface */
    result = pISystem->QueryInterface(&GID_IEcoSystem, (void **)&pISys);
    /* Check */
    if (result != 0 || pISys == 0) {
        return (int16_t)ERR_ECO_NOSYSTEM;
    }

    /* Creating the component */
    pCObj = new C[!output FIX_PROJECT_NAME](pISystem, pIUnknownOuter);

    /* Initializing the component */
    result = pCObj->Init(pISystem);

    /* Getting a pointer to the interface */
    result = pCObj->QueryInterface(riid, ppv);

    /* Decrementing the reference requested by the Component Factory */
    pCObj->Release();

    return result;
}

/*
 *
 * <summary>
 *   get_Name function
 * </summary>
 *
 * <description>
 *   The function returns the component name
 * </description>
 *
 */
char_t* ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Factory::get_Name() {
    return m_Name;
}

/*
 *
 * <summary>
 *   get_Version function
 * </summary>
 *
 * <description>
 *   The function returns the component version
 * </description>
 *
 */
char_t* ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Factory::get_Version() {
    return m_Version;
}

/*
 *
 * <summary>
 *   get_Manufacturer function
 * </summary>
 *
 * <description>
 *   The function returns the component manufacturer name
 * </description>
 *
 */
char_t* ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Factory::get_Manufacturer() {
    return m_Manufacturer;
}

/*
 *
 * <summary>
 *   Create function
 * </summary>
 *
 * <description>
 *   The function 
 * </description>
 *
 */
C[!output FIX_PROJECT_NAME]Factory g_x[!output GUID_CID_TARGET]Factory;

[!if ADD_POSTFIX_NAMESPACE]
} /* namespace [!output GUID_CID_NAMESPACE] */
[!endif]
#ifdef ECO_DLL
extern "C" ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr() {
[!if ADD_POSTFIX_NAMESPACE]	
    return static_cast<IEcoComponentFactory*>(&[!output GUID_CID_NAMESPACE]::g_x[!output GUID_CID_TARGET]Factory);
[!else]	
    return static_cast<IEcoComponentFactory*>(&g_x[!output GUID_CID_TARGET]Factory);
[!endif]	
};
#elif ECO_LIB
[!if ADD_POSTFIX_NAMESPACE]	
extern "C" IEcoComponentFactory* GetIEcoComponentFactoryPtr_[!output GUID_CID_TARGET] = (IEcoComponentFactory*)&[!output GUID_CID_NAMESPACE]::g_x[!output GUID_CID_TARGET]Factory;
[!else]	
extern "C" IEcoComponentFactory* GetIEcoComponentFactoryPtr_[!output GUID_CID_TARGET] = (IEcoComponentFactory*)&g_x[!output GUID_CID_TARGET]Factory;
[!endif]	
#endif
