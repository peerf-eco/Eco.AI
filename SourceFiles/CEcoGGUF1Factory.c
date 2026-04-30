#include "CEcoGGUF1.h"
#include "CEcoGGUF1Factory.h"

int16_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1Factory_QueryInterface(IEcoComponentFactory* me, const UGUID* riid, void** ppv) {
    if (IsEqualUGUID(riid, &IID_IEcoUnknown) || IsEqualUGUID(riid, &IID_IEcoComponentFactory)) {
        *ppv = me;
        ((IEcoUnknown*)(*ppv))->pVTbl->AddRef((IEcoUnknown*)*ppv);
        return 0;
    }

    *ppv = 0;
    return -1;
}

uint32_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1Factory_AddRef(IEcoComponentFactory* me) {
    CEcoGGUF1_6EAA44B1Factory* pCMe = (CEcoGGUF1_6EAA44B1Factory*)me;

    if (me == 0) {
        return (uint32_t)-1;
    }

    return ++pCMe->m_cRef;
}

uint32_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1Factory_Release(IEcoComponentFactory* me) {
    CEcoGGUF1_6EAA44B1Factory* pCMe = (CEcoGGUF1_6EAA44B1Factory*)me;

    if (me == 0) {
        return (uint32_t)-1;
    }

    --pCMe->m_cRef;
    return pCMe->m_cRef;
}

int16_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1Factory_Init(IEcoComponentFactory* me, IEcoUnknown* pIUnkSystem, void* pv) {
    CEcoGGUF1_6EAA44B1Factory* pCMe = (CEcoGGUF1_6EAA44B1Factory*)me;

    if (me == 0) {
        return -1;
    }

    return pCMe->m_pInitInstance(pv, pIUnkSystem);
}

int16_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1Factory_Alloc(IEcoComponentFactory* me, IEcoUnknown* pISystem, IEcoUnknown* pIUnknownOuter, const UGUID* riid, void** ppv) {
    CEcoGGUF1_6EAA44B1Factory* pCMe = (CEcoGGUF1_6EAA44B1Factory*)me;
    IEcoUnknown* pIUnk = 0;
    int16_t result = -1;

    if (me == 0) {
        return -1;
    }

    if ((pIUnknownOuter != 0) && !IsEqualUGUID(riid, &IID_IEcoUnknown)) {
        return -1;
    }

    result = pCMe->m_pInstance(pISystem, pIUnknownOuter, (void**)&pIUnk);
    if (result != 0 || pIUnk == 0) {
        return -1;
    }

    result = me->pVTbl->Init(me, pISystem, pIUnk);
    if (result == 0) {
        result = pIUnk->pVTbl->QueryInterface(pIUnk, riid, ppv);
    }

    pIUnk->pVTbl->Release(pIUnk);
    return result;
}

char_t* ECOCALLMETHOD CEcoGGUF1_6EAA44B1Factory_get_Name(IEcoComponentFactory* me) {
    CEcoGGUF1_6EAA44B1Factory* pCMe = (CEcoGGUF1_6EAA44B1Factory*)me;

    return me == 0 ? 0 : pCMe->m_Name;
}

char_t* ECOCALLMETHOD CEcoGGUF1_6EAA44B1Factory_get_Version(IEcoComponentFactory* me) {
    CEcoGGUF1_6EAA44B1Factory* pCMe = (CEcoGGUF1_6EAA44B1Factory*)me;

    return me == 0 ? 0 : pCMe->m_Version;
}

char_t* ECOCALLMETHOD CEcoGGUF1_6EAA44B1Factory_get_Manufacturer(IEcoComponentFactory* me) {
    CEcoGGUF1_6EAA44B1Factory* pCMe = (CEcoGGUF1_6EAA44B1Factory*)me;

    return me == 0 ? 0 : pCMe->m_Manufacturer;
}

static IEcoComponentFactoryVTbl g_xA1C53A779BCB4AD78B634F1A6EAA44B1FactoryVTbl = {
    CEcoGGUF1_6EAA44B1Factory_QueryInterface,
    CEcoGGUF1_6EAA44B1Factory_AddRef,
    CEcoGGUF1_6EAA44B1Factory_Release,
    CEcoGGUF1_6EAA44B1Factory_Alloc,
    CEcoGGUF1_6EAA44B1Factory_Init,
    CEcoGGUF1_6EAA44B1Factory_get_Name,
    CEcoGGUF1_6EAA44B1Factory_get_Version,
    CEcoGGUF1_6EAA44B1Factory_get_Manufacturer
};

static CEcoGGUF1_6EAA44B1Factory g_xA1C53A779BCB4AD78B634F1A6EAA44B1Factory = {
    &g_xA1C53A779BCB4AD78B634F1A6EAA44B1FactoryVTbl,
    0,
    (CreateInstance)createCEcoGGUF1_6EAA44B1,
    (InitInstance)initCEcoGGUF1_6EAA44B1,
    "EcoGGUF1",
    "1.0.0.0",
    "CompanyName"
};

#ifdef ECO_DLL
IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr() {
    return (IEcoComponentFactory*)&g_xA1C53A779BCB4AD78B634F1A6EAA44B1Factory;
}
#elif ECO_LIB
IEcoComponentFactory* GetIEcoComponentFactoryPtr_A1C53A779BCB4AD78B634F1A6EAA44B1 = (IEcoComponentFactory*)&g_xA1C53A779BCB4AD78B634F1A6EAA44B1Factory;
#endif
