/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   [!output FIX_PROJECT_NAME]
 * </summary>
 *
 * <description>
 *   This source file is the entry point
 * </description>
 *
 * <author>
 *   Copyright (c) 2026 [!output AUTHOR]. All rights reserved.
 * </author>
 *
 */


/* Eco OS */
#include "IEcoSystem1.hpp"
#include "IdEcoMemoryManager1.hpp"
#include "IdEcoInterfaceBus1.hpp"
#include "IdEcoFileSystemManagement1.hpp"
#include "Id[!output FIX_PROJECT_NAME].hpp"

[!if ADD_CONNECTION_POINTS]
#include "C[!output FIX_PROJECT_NAME]Sink.hpp"
#include "IEcoConnectionPointContainer.hpp"
[!endif]

/*
 *
 * <summary>
 *   EcoMain Function
 * </summary>
 *
 * <description>
 *   EcoMain function - entry point
 * </description>
 *
 */
extern "C" int16_t EcoMain(IEcoUnknown* pIUnk) {
    int16_t result = -1;
    /* Pointer to the system interface */
    IEcoSystem1* pISys = 0;
    /* Pointer to the interface for working with the system interface bus */
    IEcoInterfaceBus1* pIBus = 0;
    /* Pointer to the memory management interface */
    IEcoMemoryAllocator1* pIMem = 0;
    char_t* name = 0;
[!if ECO_COM_APP]
    char_t* copyName = 0;
    /* Pointer to the tested interface */
    I[!output FIX_PROJECT_NAME]* pI[!output FIX_PROJECT_NAME] = 0;
[!endif]
[!if ADD_CONNECTION_POINTS]
    /* Pointer to the connection points container interface */
    IEcoConnectionPointContainer* pICPC = 0;
    /* Pointer to the connection point interface */
    IEcoConnectionPoint* pICP = 0;
    /* Pointer to the reverse interface (sink) */
    I[!output FIX_PROJECT_NAME]Events* pI[!output FIX_PROJECT_NAME]Sink = 0;
    IEcoUnknown* pISinkUnk = 0;
    uint32_t cAdvise = 0;
[!endif]

    /* System interface check and creation */
    if (pISys == 0) {
        result = pIUnk->QueryInterface(&GID_IEcoSystem, (void **)&pISys);
        if (result != 0 && pISys == 0) {
        /* Free the system interface in case of an error */
            goto Release;
        }
    }

    /* Getting the interface for working with the interface bus */
    result = pISys->QueryInterface(&IID_IEcoInterfaceBus1, (void **)&pIBus);
    if (result != 0 || pIBus == 0) {
        /* Free in case of an error */
        goto Release;
    }
[!if ECO_COM_APP]
#ifdef ECO_LIB
    /* Registration of a static component for working with the list */
    result = pIBus->RegisterComponent(&CID_[!output FIX_PROJECT_NAME], (IEcoUnknown*)GetIEcoComponentFactoryPtr_[!output GUID_CID_TARGET]);
    if (result != 0 ) {
        /* Free in case of an error */
        goto Release;
    }
#endif
[!endif]
    /* Getting the memory management interface */
    result = pIBus->QueryComponent(&CID_EcoMemoryManager1, 0, &IID_IEcoMemoryAllocator1, (void**) &pIMem);

    /* Check */
    if (result != 0 || pIMem == 0) {
        /* Free the system interface in case of an error */
        goto Release;
    }

    /* Memory block allocation */
    name = (char_t *)pIMem->Alloc(10);

    /* Fill the memory block */
    pIMem->Fill(name, 'a', 9);

[!if ECO_COM_APP]

    /* Getting the tested interface */
    result = pIBus->QueryComponent(&CID_[!output FIX_PROJECT_NAME], 0, &IID_I[!output FIX_PROJECT_NAME], (void**) &pI[!output FIX_PROJECT_NAME]);
    if (result != 0 || pI[!output FIX_PROJECT_NAME] == 0) {
        /* Free interfaces in case of an error */
        goto Release;
    }

[!if ADD_CONNECTION_POINTS]
    /* Checking support for reverse interface connections */
    result = pI[!output FIX_PROJECT_NAME]->QueryInterface(&IID_IEcoConnectionPointContainer, (void **)&pICPC);
    if (result != 0 || pICPC == 0) {
        /* Free interfaces in case of an error */
        goto Release;
    }

    /* Request to get the connection point interface */
    result = pICPC->FindConnectionPoint(&IID_I[!output FIX_PROJECT_NAME]Events, &pICP);
    if (result != 0 || pICP == 0) {
        /* Free interfaces in case of an error */
        goto Release;
    }
    /* Free the interface */
    pICPC->Release();

    /* Create an instance of the reverse interface */
    result = createC[!output FIX_PROJECT_NAME]Sink(pIMem, (I[!output FIX_PROJECT_NAME]Events**)&pI[!output FIX_PROJECT_NAME]Sink);

    if (pI[!output FIX_PROJECT_NAME]Sink != 0) {
        result = pI[!output FIX_PROJECT_NAME]Sink->pVTbl->QueryInterface(pI[!output FIX_PROJECT_NAME]Sink, &IID_IEcoUnknown,(void **)&pISinkUnk);
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

    result = pI[!output FIX_PROJECT_NAME]->MyFunction(name, &copyName);

[!endif]

    /* Free the memory block */
    pIMem->Free(name);

Release:

    /* Free the interface for working with the interface bus */
    if (pIBus != 0) {
        pIBus->Release();
    }

    /* Free the memory management interface */
    if (pIMem != 0) {
        pIMem->Release();
    }

[!if ECO_COM_APP]
    /* Free the tested interface */
    if (pI[!output FIX_PROJECT_NAME] != 0) {
        pI[!output FIX_PROJECT_NAME]->Release();
    }

[!endif]

    /* Free the system interface */
    if (pISys != 0) {
        pISys->Release();
    }

    return result;
}

