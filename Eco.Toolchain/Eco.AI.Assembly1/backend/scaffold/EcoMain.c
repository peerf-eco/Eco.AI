/*
 * EcoMain.c — EcoOS entry-point skeleton (PROVEN pattern; validated 2026-06-01).
 *
 * KEY FACTS — do not fight them, they are how this SDK works:
 *  - The real main() lives in Eco.System1 (lib...53595333.a). It bootstraps
 *    the system and then calls EcoMain(pIUnk). Writing your own main() will
 *    link but crash: factories need a live system pointer you cannot forge.
 *  - Register every component you pulled on the bus under #ifdef ECO_LIB,
 *    then QueryComponent to obtain its interface.
 *  - Factory symbol name is GetIEcoComponentFactoryPtr_<UGUID> where <UGUID>
 *    is the component's .a file name without the 'lib' prefix / '.a' suffix.
 */
#include <stdio.h>
#include "IEcoSystem1.h"
#include "IEcoInterfaceBus1.h"
#include "IdEcoInterfaceBus1.h"
#include "IdEcoMemoryManager1.h"
#include "IdEcoFileSystemManagement1.h"
/* TODO: #include the I*.h / Id*.h headers of the task components you pulled. */

static IEcoSystem1*       g_pISys = 0;
static IEcoInterfaceBus1* g_pIBus = 0;

int16_t EcoMain(IEcoUnknown* pIUnk) {
    int16_t result = -1;

    result = pIUnk->pVTbl->QueryInterface(pIUnk, &GID_IEcoSystem, (void**)&g_pISys);
    if (result != 0 || g_pISys == 0) goto Release;

    result = g_pISys->pVTbl->QueryInterface(g_pISys, &IID_IEcoInterfaceBus1, (void**)&g_pIBus);
    if (result != 0 || g_pIBus == 0) goto Release;

#ifdef ECO_LIB
    /* Framework components first, then the task components. */
    g_pIBus->pVTbl->RegisterComponent(g_pIBus, &CID_EcoInterfaceBus1,
        (IEcoUnknown*)GetIEcoComponentFactoryPtr_00000000000000000000000042757331);
    g_pIBus->pVTbl->RegisterComponent(g_pIBus, &CID_EcoFileSystemManagement1,
        (IEcoUnknown*)GetIEcoComponentFactoryPtr_00000000000000000000000046534D31);
    /* TODO: RegisterComponent(...) for each task component you pulled. */
#endif

    /* TODO: QueryComponent(...) the interfaces you need and implement the task.
     * Pattern:
     *   g_pIBus->pVTbl->QueryComponent(g_pIBus, &CID_X, 0, &IID_IX, (void**)&pIX);
     *   ... use pIX->pVTbl->method(pIX, ...) ...
     *   pIX->pVTbl->Release(pIX);
     */

    result = 0;
Release:
    if (g_pIBus) g_pIBus->pVTbl->Release(g_pIBus);
    if (g_pISys) g_pISys->pVTbl->Release(g_pISys);
    return result;
}
