#include "CEcoGGUF1RawData.h"
#include "IEcoSystem1.h"
#include "IEcoInterfaceBus1.h"

int16_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1RawData_QueryInterface(IEcoRawData1Ptr_t me, const UGUID* riid, voidptr_t* ppv) {
    if (me == 0 || ppv == 0) {
        return -1;
    }

    if (IsEqualUGUID(riid, &IID_IEcoRawData1) || IsEqualUGUID(riid, &IID_IEcoUnknown)) {
        *ppv = me;
        me->pVTbl->AddRef(me);
        return 0;
    }

    *ppv = 0;
    return -1;
}

uint32_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1RawData_AddRef(IEcoRawData1Ptr_t me) {
    CEcoGGUF1_6EAA44B1RawData* pCMe = (CEcoGGUF1_6EAA44B1RawData*)me;

    if (me == 0) {
        return (uint32_t)-1;
    }

    return ++pCMe->m_cRef;
}

void ECOCALLMETHOD deleteCEcoGGUF1_6EAA44B1RawData(IEcoRawData1* pIRawData) {
    CEcoGGUF1_6EAA44B1RawData* pCMe = (CEcoGGUF1_6EAA44B1RawData*)pIRawData;
    IEcoMemoryAllocator1* pIMem = 0;

    if (pCMe == 0) {
        return;
    }

    pIMem = pCMe->m_pIMem;

    if (pCMe->m_pData != 0 && pIMem != 0) {
        pIMem->pVTbl->Free(pIMem, pCMe->m_pData);
        pCMe->m_pData = 0;
    }

    if (pCMe->m_pISys != 0) {
        pCMe->m_pISys->pVTbl->Release(pCMe->m_pISys);
    }

    if (pIMem != 0) {
        pIMem->pVTbl->Free(pIMem, pCMe);
        pIMem->pVTbl->Release(pIMem);
    }
}

uint32_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1RawData_Release(IEcoRawData1Ptr_t me) {
    CEcoGGUF1_6EAA44B1RawData* pCMe = (CEcoGGUF1_6EAA44B1RawData*)me;

    if (me == 0) {
        return (uint32_t)-1;
    }

    --pCMe->m_cRef;
    if (pCMe->m_cRef == 0) {
        deleteCEcoGGUF1_6EAA44B1RawData((IEcoRawData1*)pCMe);
        return 0;
    }

    return pCMe->m_cRef;
}

byte_t* ECOCALLMETHOD CEcoGGUF1_6EAA44B1RawData_Alloc(IEcoRawData1Ptr_t me, uint32_t size) {
    CEcoGGUF1_6EAA44B1RawData* pCMe = (CEcoGGUF1_6EAA44B1RawData*)me;

    if (me == 0 || pCMe->m_pIMem == 0) {
        return 0;
    }

    if (pCMe->m_pData != 0) {
        pCMe->m_pIMem->pVTbl->Free(pCMe->m_pIMem, pCMe->m_pData);
        pCMe->m_pData = 0;
        pCMe->m_Size = 0;
    }

    if (size == 0) {
        return 0;
    }

    pCMe->m_pData = (byte_t*)pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, size);
    pCMe->m_Size = pCMe->m_pData != 0 ? size : 0;
    return pCMe->m_pData;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1RawData_Fill(IEcoRawData1Ptr_t me, byte_t value) {
    CEcoGGUF1_6EAA44B1RawData* pCMe = (CEcoGGUF1_6EAA44B1RawData*)me;
    uint32_t index = 0;

    if (me == 0 || pCMe->m_pData == 0) {
        return;
    }

    for (index = 0; index < pCMe->m_Size; ++index) {
        pCMe->m_pData[index] = value;
    }
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1RawData_Free(IEcoRawData1Ptr_t me) {
    CEcoGGUF1_6EAA44B1RawData* pCMe = (CEcoGGUF1_6EAA44B1RawData*)me;

    if (me == 0 || pCMe->m_pIMem == 0 || pCMe->m_pData == 0) {
        return;
    }

    pCMe->m_pIMem->pVTbl->Free(pCMe->m_pIMem, pCMe->m_pData);
    pCMe->m_pData = 0;
    pCMe->m_Size = 0;
}

uint32_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1RawData_get_Size(IEcoRawData1Ptr_t me) {
    CEcoGGUF1_6EAA44B1RawData* pCMe = (CEcoGGUF1_6EAA44B1RawData*)me;

    return me == 0 ? 0 : pCMe->m_Size;
}

byte_t* ECOCALLMETHOD CEcoGGUF1_6EAA44B1RawData_get_Pointer(IEcoRawData1Ptr_t me, uint32_t offset) {
    CEcoGGUF1_6EAA44B1RawData* pCMe = (CEcoGGUF1_6EAA44B1RawData*)me;

    if (me == 0 || pCMe->m_pData == 0 || offset >= pCMe->m_Size) {
        return 0;
    }

    return pCMe->m_pData + offset;
}

static IEcoRawData1VTbl g_xEcoGGUF1RawDataVTbl = {
    CEcoGGUF1_6EAA44B1RawData_QueryInterface,
    CEcoGGUF1_6EAA44B1RawData_AddRef,
    CEcoGGUF1_6EAA44B1RawData_Release,
    CEcoGGUF1_6EAA44B1RawData_Alloc,
    CEcoGGUF1_6EAA44B1RawData_Fill,
    CEcoGGUF1_6EAA44B1RawData_Free,
    CEcoGGUF1_6EAA44B1RawData_get_Size,
    CEcoGGUF1_6EAA44B1RawData_get_Pointer
};

int16_t ECOCALLMETHOD createCEcoGGUF1_6EAA44B1RawData(IEcoUnknown* pIUnkSystem, IEcoUnknown* pIUnkOuter, IEcoRawData1** ppIRawData) {
    IEcoSystem1* pISys = 0;
    IEcoInterfaceBus1* pIBus = 0;
    IEcoMemoryAllocator1* pIMem = 0;
    CEcoGGUF1_6EAA44B1RawData* pCMe = 0;
    int16_t result = -1;

    (void)pIUnkOuter;

    if (ppIRawData == 0 || pIUnkSystem == 0) {
        return -1;
    }

    *ppIRawData = 0;

    result = pIUnkSystem->pVTbl->QueryInterface(pIUnkSystem, &GID_IEcoSystem, (void**)&pISys);
    if (result != 0 || pISys == 0) {
        return -1;
    }

    result = pISys->pVTbl->QueryInterface(pISys, &IID_IEcoInterfaceBus1, (void**)&pIBus);
    if (result != 0 || pIBus == 0) {
        pISys->pVTbl->Release(pISys);
        return -1;
    }

    result = pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoMemoryManager1, 0, &IID_IEcoMemoryAllocator1, (void**)&pIMem);
    pIBus->pVTbl->Release(pIBus);
    if (result != 0 || pIMem == 0) {
        pISys->pVTbl->Release(pISys);
        return -1;
    }

    pCMe = (CEcoGGUF1_6EAA44B1RawData*)pIMem->pVTbl->Alloc(pIMem, sizeof(CEcoGGUF1_6EAA44B1RawData));
    if (pCMe == 0) {
        pIMem->pVTbl->Release(pIMem);
        pISys->pVTbl->Release(pISys);
        return -1;
    }

    pCMe->m_pVTblIRawData = &g_xEcoGGUF1RawDataVTbl;
    pCMe->m_cRef = 1;
    pCMe->m_pIMem = pIMem;
    pCMe->m_pISys = pISys;
    pCMe->m_pData = 0;
    pCMe->m_Size = 0;

    *ppIRawData = (IEcoRawData1*)pCMe;
    return 0;
}
