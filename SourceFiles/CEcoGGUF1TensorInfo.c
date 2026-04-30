#include "CEcoGGUF1TensorInfo.h"
#include "IEcoSystem1.h"
#include "IEcoInterfaceBus1.h"

static uint64_t CEcoGGUF1_TensorInfo_strlen(const char_t* value) {
    uint64_t len = 0;

    if (value == 0) {
        return 0;
    }

    while (value[len] != 0) {
        ++len;
    }

    return len;
}

int16_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1TensorInfo_QueryInterface(IEcoGGUF1TensorInfoPtr_t me, const UGUID* riid, voidptr_t* ppv) {
    if (me == 0 || ppv == 0) {
        return -1;
    }

    if (IsEqualUGUID(riid, &IID_IEcoGGUF1TensorInfo) || IsEqualUGUID(riid, &IID_IEcoUnknown)) {
        *ppv = me;
        me->pVTbl->AddRef(me);
        return 0;
    }

    *ppv = 0;
    return -1;
}

uint32_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1TensorInfo_AddRef(IEcoGGUF1TensorInfoPtr_t me) {
    CEcoGGUF1_6EAA44B1TensorInfo* pCMe = (CEcoGGUF1_6EAA44B1TensorInfo*)me;

    if (me == 0) {
        return (uint32_t)-1;
    }

    return ++pCMe->m_cRef;
}

void ECOCALLMETHOD deleteCEcoGGUF1_6EAA44B1TensorInfo(IEcoGGUF1TensorInfo* pIInfo) {
    CEcoGGUF1_6EAA44B1TensorInfo* pCMe = (CEcoGGUF1_6EAA44B1TensorInfo*)pIInfo;
    IEcoMemoryAllocator1* pIMem = 0;

    if (pCMe == 0) {
        return;
    }

    pIMem = pCMe->m_pIMem;

    if (pCMe->m_pIRawData != 0) {
        pCMe->m_pIRawData->pVTbl->Release(pCMe->m_pIRawData);
    }

    if (pCMe->m_pIStr != 0) {
        pCMe->m_pIStr->pVTbl->Release(pCMe->m_pIStr);
    }

    if (pCMe->m_pISys != 0) {
        pCMe->m_pISys->pVTbl->Release(pCMe->m_pISys);
    }

    if (pIMem != 0) {
        pIMem->pVTbl->Free(pIMem, pCMe);
        pIMem->pVTbl->Release(pIMem);
    }
}

uint32_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1TensorInfo_Release(IEcoGGUF1TensorInfoPtr_t me) {
    CEcoGGUF1_6EAA44B1TensorInfo* pCMe = (CEcoGGUF1_6EAA44B1TensorInfo*)me;

    if (me == 0) {
        return (uint32_t)-1;
    }

    --pCMe->m_cRef;
    if (pCMe->m_cRef == 0) {
        deleteCEcoGGUF1_6EAA44B1TensorInfo((IEcoGGUF1TensorInfo*)pCMe);
        return 0;
    }

    return pCMe->m_cRef;
}

ECO_GGUF1_TENSOR_INFO_DESCRIPTOR* ECOCALLMETHOD CEcoGGUF1_6EAA44B1TensorInfo_get_Descriptor(IEcoGGUF1TensorInfoPtr_t me) {
    CEcoGGUF1_6EAA44B1TensorInfo* pCMe = (CEcoGGUF1_6EAA44B1TensorInfo*)me;

    return me == 0 ? 0 : &pCMe->m_Descriptor;
}

char_t* ECOCALLMETHOD CEcoGGUF1_6EAA44B1TensorInfo_get_Name(IEcoGGUF1TensorInfoPtr_t me) {
    CEcoGGUF1_6EAA44B1TensorInfo* pCMe = (CEcoGGUF1_6EAA44B1TensorInfo*)me;

    return me == 0 ? 0 : pCMe->m_Descriptor.name;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1TensorInfo_set_Name(IEcoGGUF1TensorInfoPtr_t me, char_t* name) {
    CEcoGGUF1_6EAA44B1TensorInfo* pCMe = (CEcoGGUF1_6EAA44B1TensorInfo*)me;
    uint64_t index = 0;
    uint64_t len = 0;

    if (me == 0) {
        return;
    }

    pCMe->m_Descriptor.name[0] = 0;
    pCMe->m_Descriptor.name_length = 0;

    if (name == 0) {
        return;
    }

    len = CEcoGGUF1_TensorInfo_strlen(name);
    if (len > ECO_GGUF1_MAX_TENSOR_NAME) {
        len = ECO_GGUF1_MAX_TENSOR_NAME;
    }

    for (index = 0; index < len; ++index) {
        pCMe->m_Descriptor.name[index] = name[index];
    }
    pCMe->m_Descriptor.name[len] = 0;
    pCMe->m_Descriptor.name_length = len;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1TensorInfo_set_Descriptor(IEcoGGUF1TensorInfoPtr_t me, ECO_GGUF1_TENSOR_INFO_DESCRIPTOR* descriptor) {
    CEcoGGUF1_6EAA44B1TensorInfo* pCMe = (CEcoGGUF1_6EAA44B1TensorInfo*)me;
    uint32_t index = 0;

    if (me == 0 || descriptor == 0) {
        return;
    }

    me->pVTbl->set_Name(me, descriptor->name);
    pCMe->m_Descriptor.n_dimensions = descriptor->n_dimensions;
    if (pCMe->m_Descriptor.n_dimensions > ECO_GGUF1_MAX_DIMS) {
        pCMe->m_Descriptor.n_dimensions = ECO_GGUF1_MAX_DIMS;
    }

    for (index = 0; index < ECO_GGUF1_MAX_DIMS; ++index) {
        pCMe->m_Descriptor.dimensions[index] = descriptor->dimensions[index];
    }

    pCMe->m_Descriptor.type = descriptor->type;
    pCMe->m_Descriptor.offset = descriptor->offset;
}

IEcoUnknown* ECOCALLMETHOD CEcoGGUF1_6EAA44B1TensorInfo_get_RawData(IEcoGGUF1TensorInfoPtr_t me) {
    CEcoGGUF1_6EAA44B1TensorInfo* pCMe = (CEcoGGUF1_6EAA44B1TensorInfo*)me;

    return me == 0 ? 0 : pCMe->m_pIRawData;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1TensorInfo_set_RawData(IEcoGGUF1TensorInfoPtr_t me, IEcoUnknown* pIRawData) {
    CEcoGGUF1_6EAA44B1TensorInfo* pCMe = (CEcoGGUF1_6EAA44B1TensorInfo*)me;

    if (me == 0) {
        return;
    }

    if (pCMe->m_pIRawData != 0) {
        pCMe->m_pIRawData->pVTbl->Release(pCMe->m_pIRawData);
    }

    pCMe->m_pIRawData = pIRawData;
    if (pCMe->m_pIRawData != 0) {
        pCMe->m_pIRawData->pVTbl->AddRef(pCMe->m_pIRawData);
    }
}

static IEcoGGUF1TensorInfoVTbl g_xEcoGGUF1TensorInfoVTbl = {
    CEcoGGUF1_6EAA44B1TensorInfo_QueryInterface,
    CEcoGGUF1_6EAA44B1TensorInfo_AddRef,
    CEcoGGUF1_6EAA44B1TensorInfo_Release,
    CEcoGGUF1_6EAA44B1TensorInfo_get_Descriptor,
    CEcoGGUF1_6EAA44B1TensorInfo_set_Descriptor,
    CEcoGGUF1_6EAA44B1TensorInfo_get_Name,
    CEcoGGUF1_6EAA44B1TensorInfo_set_Name,
    CEcoGGUF1_6EAA44B1TensorInfo_get_RawData,
    CEcoGGUF1_6EAA44B1TensorInfo_set_RawData
};

int16_t ECOCALLMETHOD createCEcoGGUF1_6EAA44B1TensorInfo(IEcoUnknown* pIUnkSystem, IEcoUnknown* pIUnkOuter, IEcoGGUF1TensorInfo** ppIInfo) {
    IEcoSystem1* pISys = 0;
    IEcoInterfaceBus1* pIBus = 0;
    IEcoMemoryAllocator1* pIMem = 0;
    IEcoString1* pIStr = 0;
    CEcoGGUF1_6EAA44B1TensorInfo* pCMe = 0;
    int16_t result = -1;
    uint32_t index = 0;

    (void)pIUnkOuter;

    if (ppIInfo == 0 || pIUnkSystem == 0) {
        return -1;
    }

    *ppIInfo = 0;

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
    if (result == 0) {
        pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoString1, 0, &IID_IEcoString1, (void**)&pIStr);
    }
    pIBus->pVTbl->Release(pIBus);

    if (result != 0 || pIMem == 0) {
        if (pIStr != 0) {
            pIStr->pVTbl->Release(pIStr);
        }
        pISys->pVTbl->Release(pISys);
        return -1;
    }

    pCMe = (CEcoGGUF1_6EAA44B1TensorInfo*)pIMem->pVTbl->Alloc(pIMem, sizeof(CEcoGGUF1_6EAA44B1TensorInfo));
    if (pCMe == 0) {
        if (pIStr != 0) {
            pIStr->pVTbl->Release(pIStr);
        }
        pIMem->pVTbl->Release(pIMem);
        pISys->pVTbl->Release(pISys);
        return -1;
    }

    pCMe->m_pVTblITensorInfo = &g_xEcoGGUF1TensorInfoVTbl;
    pCMe->m_cRef = 1;
    pCMe->m_pIMem = pIMem;
    pCMe->m_pISys = pISys;
    pCMe->m_pIStr = pIStr;
    pCMe->m_pIRawData = 0;
    pCMe->m_Descriptor.name_length = 0;
    pCMe->m_Descriptor.name[0] = 0;
    pCMe->m_Descriptor.n_dimensions = 0;
    for (index = 0; index < ECO_GGUF1_MAX_DIMS; ++index) {
        pCMe->m_Descriptor.dimensions[index] = 0;
    }
    pCMe->m_Descriptor.type = ECO_GGUF1_TENSOR_TYPE_F32;
    pCMe->m_Descriptor.offset = 0;

    *ppIInfo = (IEcoGGUF1TensorInfo*)pCMe;
    return 0;
}
