#include "CEcoGGUF1File.h"
#include "IEcoSystem1.h"
#include "IEcoInterfaceBus1.h"

static uint64_t CEcoGGUF1_File_strlen(const char_t* value) {
    uint64_t len = 0;

    if (value == 0) {
        return 0;
    }

    while (value[len] != 0) {
        ++len;
    }

    return len;
}

static void CEcoGGUF1_File_clearTensorDataSource(CEcoGGUF1_6EAA44B1File* pCMe) {
    if (pCMe == 0) {
        return;
    }

    if (pCMe->m_TensorDataSourcePath != 0 && pCMe->m_pIMem != 0) {
        pCMe->m_pIMem->pVTbl->Free(pCMe->m_pIMem, pCMe->m_TensorDataSourcePath);
    }
    pCMe->m_TensorDataSourcePath = 0;
    pCMe->m_TensorDataSourceOffset = 0;
    pCMe->m_TensorDataSourceSize = 0;
}

int16_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_QueryInterface(IEcoGGUF1FilePtr_t me, const UGUID* riid, voidptr_t* ppv) {
    if (me == 0 || ppv == 0) {
        return -1;
    }

    if (IsEqualUGUID(riid, &IID_IEcoGGUF1File) || IsEqualUGUID(riid, &IID_IEcoUnknown)) {
        *ppv = me;
        me->pVTbl->AddRef(me);
        return 0;
    }

    *ppv = 0;
    return -1;
}

uint32_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_AddRef(IEcoGGUF1FilePtr_t me) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)me;

    if (me == 0) {
        return (uint32_t)-1;
    }

    return ++pCMe->m_cRef;
}

void ECOCALLMETHOD deleteCEcoGGUF1_6EAA44B1File(IEcoGGUF1File* pIFile) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)pIFile;
    IEcoMemoryAllocator1* pIMem = 0;

    if (pCMe == 0) {
        return;
    }

    pIMem = pCMe->m_pIMem;

    if (pCMe->m_pIMetadataKVs != 0) {
        pCMe->m_pIMetadataKVs->pVTbl->Release(pCMe->m_pIMetadataKVs);
    }

    if (pCMe->m_pITensorInfos != 0) {
        pCMe->m_pITensorInfos->pVTbl->Release(pCMe->m_pITensorInfos);
    }

    if (pCMe->m_pITensorData != 0) {
        pCMe->m_pITensorData->pVTbl->Release(pCMe->m_pITensorData);
    }

    CEcoGGUF1_File_clearTensorDataSource(pCMe);

    if (pCMe->m_pISys != 0) {
        pCMe->m_pISys->pVTbl->Release(pCMe->m_pISys);
    }

    if (pIMem != 0) {
        pIMem->pVTbl->Free(pIMem, pCMe);
        pIMem->pVTbl->Release(pIMem);
    }
}

uint32_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_Release(IEcoGGUF1FilePtr_t me) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)me;

    if (me == 0) {
        return (uint32_t)-1;
    }

    --pCMe->m_cRef;
    if (pCMe->m_cRef == 0) {
        deleteCEcoGGUF1_6EAA44B1File((IEcoGGUF1File*)pCMe);
        return 0;
    }

    return pCMe->m_cRef;
}

ECO_GGUF1_HEADER_DESCRIPTOR* ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_get_Descriptor(IEcoGGUF1FilePtr_t me) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)me;

    return me == 0 ? 0 : &pCMe->m_Descriptor;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_set_Descriptor(IEcoGGUF1FilePtr_t me, ECO_GGUF1_HEADER_DESCRIPTOR* descriptor) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)me;

    if (me == 0 || descriptor == 0) {
        return;
    }

    pCMe->m_Descriptor.magic = descriptor->magic;
    pCMe->m_Descriptor.version = descriptor->version;
    pCMe->m_Descriptor.tensor_count = descriptor->tensor_count;
    pCMe->m_Descriptor.metadata_kv_count = descriptor->metadata_kv_count;
    pCMe->m_Descriptor.tensor_data_offset = descriptor->tensor_data_offset;
}

uint32_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_get_Alignment(IEcoGGUF1FilePtr_t me) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)me;

    return me == 0 ? 0 : pCMe->m_Alignment;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_set_Alignment(IEcoGGUF1FilePtr_t me, uint32_t alignment) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)me;

    if (me == 0) {
        return;
    }

    pCMe->m_Alignment = alignment == 0 ? ECO_GGUF1_DEFAULT_ALIGNMENT : alignment;
}

IEcoList1* ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_get_MetadataKVs(IEcoGGUF1FilePtr_t me) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)me;

    return me == 0 ? 0 : pCMe->m_pIMetadataKVs;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_set_MetadataKVs(IEcoGGUF1FilePtr_t me, IEcoList1* pIEntries) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)me;

    if (me == 0) {
        return;
    }

    if (pCMe->m_pIMetadataKVs != 0) {
        pCMe->m_pIMetadataKVs->pVTbl->Release(pCMe->m_pIMetadataKVs);
    }

    pCMe->m_pIMetadataKVs = pIEntries;
    if (pCMe->m_pIMetadataKVs != 0) {
        pCMe->m_pIMetadataKVs->pVTbl->AddRef(pCMe->m_pIMetadataKVs);
        pCMe->m_Descriptor.metadata_kv_count = pCMe->m_pIMetadataKVs->pVTbl->Count(pCMe->m_pIMetadataKVs);
    }
    else {
        pCMe->m_Descriptor.metadata_kv_count = 0;
    }
}

IEcoList1* ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_get_TensorInfos(IEcoGGUF1FilePtr_t me) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)me;

    return me == 0 ? 0 : pCMe->m_pITensorInfos;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_set_TensorInfos(IEcoGGUF1FilePtr_t me, IEcoList1* pIInfos) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)me;

    if (me == 0) {
        return;
    }

    if (pCMe->m_pITensorInfos != 0) {
        pCMe->m_pITensorInfos->pVTbl->Release(pCMe->m_pITensorInfos);
    }

    pCMe->m_pITensorInfos = pIInfos;
    if (pCMe->m_pITensorInfos != 0) {
        pCMe->m_pITensorInfos->pVTbl->AddRef(pCMe->m_pITensorInfos);
        pCMe->m_Descriptor.tensor_count = pCMe->m_pITensorInfos->pVTbl->Count(pCMe->m_pITensorInfos);
    }
    else {
        pCMe->m_Descriptor.tensor_count = 0;
    }
}

IEcoUnknown* ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_get_TensorData(IEcoGGUF1FilePtr_t me) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)me;

    return me == 0 ? 0 : pCMe->m_pITensorData;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_set_TensorData(IEcoGGUF1FilePtr_t me, IEcoUnknown* pIRawData) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)me;

    if (me == 0) {
        return;
    }

    if (pCMe->m_pITensorData != 0) {
        pCMe->m_pITensorData->pVTbl->Release(pCMe->m_pITensorData);
    }

    pCMe->m_pITensorData = pIRawData;
    if (pCMe->m_pITensorData != 0) {
        CEcoGGUF1_File_clearTensorDataSource(pCMe);
        pCMe->m_pITensorData->pVTbl->AddRef(pCMe->m_pITensorData);
    }
}

char_t* ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_get_TensorDataSourcePath(IEcoGGUF1FilePtr_t me) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)me;

    return me == 0 ? 0 : pCMe->m_TensorDataSourcePath;
}

uint64_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_get_TensorDataSourceOffset(IEcoGGUF1FilePtr_t me) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)me;

    return me == 0 ? 0 : pCMe->m_TensorDataSourceOffset;
}

uint64_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_get_TensorDataSourceSize(IEcoGGUF1FilePtr_t me) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)me;

    return me == 0 ? 0 : pCMe->m_TensorDataSourceSize;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1File_set_TensorDataSource(IEcoGGUF1FilePtr_t me, char_t* path, uint64_t offset, uint64_t size) {
    CEcoGGUF1_6EAA44B1File* pCMe = (CEcoGGUF1_6EAA44B1File*)me;
    uint64_t len = 0;
    char_t* pNewPath = 0;
    uint64_t index = 0;

    if (me == 0 || pCMe->m_pIMem == 0) {
        return;
    }

    CEcoGGUF1_File_clearTensorDataSource(pCMe);

    if (path == 0) {
        return;
    }

    len = CEcoGGUF1_File_strlen(path);
    if (len > (uint64_t)((uint32_t)-1) - 1u) {
        return;
    }

    pNewPath = (char_t*)pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, (uint32_t)(len + 1u));
    if (pNewPath == 0) {
        return;
    }

    for (index = 0; index < len; ++index) {
        pNewPath[index] = path[index];
    }
    pNewPath[len] = 0;

    if (pCMe->m_pITensorData != 0) {
        pCMe->m_pITensorData->pVTbl->Release(pCMe->m_pITensorData);
        pCMe->m_pITensorData = 0;
    }

    pCMe->m_TensorDataSourcePath = pNewPath;
    pCMe->m_TensorDataSourceOffset = offset;
    pCMe->m_TensorDataSourceSize = size;
}

static IEcoGGUF1FileVTbl g_xEcoGGUF1FileVTbl = {
    CEcoGGUF1_6EAA44B1File_QueryInterface,
    CEcoGGUF1_6EAA44B1File_AddRef,
    CEcoGGUF1_6EAA44B1File_Release,
    CEcoGGUF1_6EAA44B1File_get_Descriptor,
    CEcoGGUF1_6EAA44B1File_set_Descriptor,
    CEcoGGUF1_6EAA44B1File_get_Alignment,
    CEcoGGUF1_6EAA44B1File_set_Alignment,
    CEcoGGUF1_6EAA44B1File_get_MetadataKVs,
    CEcoGGUF1_6EAA44B1File_set_MetadataKVs,
    CEcoGGUF1_6EAA44B1File_get_TensorInfos,
    CEcoGGUF1_6EAA44B1File_set_TensorInfos,
    CEcoGGUF1_6EAA44B1File_get_TensorData,
    CEcoGGUF1_6EAA44B1File_set_TensorData,
    CEcoGGUF1_6EAA44B1File_get_TensorDataSourcePath,
    CEcoGGUF1_6EAA44B1File_get_TensorDataSourceOffset,
    CEcoGGUF1_6EAA44B1File_get_TensorDataSourceSize,
    CEcoGGUF1_6EAA44B1File_set_TensorDataSource
};

int16_t ECOCALLMETHOD createCEcoGGUF1_6EAA44B1File(IEcoUnknown* pIUnkSystem, IEcoUnknown* pIUnkOuter, IEcoGGUF1File** ppIFile) {
    IEcoSystem1* pISys = 0;
    IEcoInterfaceBus1* pIBus = 0;
    IEcoMemoryAllocator1* pIMem = 0;
    CEcoGGUF1_6EAA44B1File* pCMe = 0;
    int16_t result = -1;

    (void)pIUnkOuter;

    if (ppIFile == 0 || pIUnkSystem == 0) {
        return -1;
    }

    *ppIFile = 0;

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

    pCMe = (CEcoGGUF1_6EAA44B1File*)pIMem->pVTbl->Alloc(pIMem, sizeof(CEcoGGUF1_6EAA44B1File));
    if (pCMe == 0) {
        pIMem->pVTbl->Release(pIMem);
        pISys->pVTbl->Release(pISys);
        return -1;
    }

    pCMe->m_pVTblIFile = &g_xEcoGGUF1FileVTbl;
    pCMe->m_cRef = 1;
    pCMe->m_pIMem = pIMem;
    pCMe->m_pISys = pISys;
    pCMe->m_Descriptor.magic = ECO_GGUF1_MAGIC;
    pCMe->m_Descriptor.version = ECO_GGUF1_VERSION_3;
    pCMe->m_Descriptor.tensor_count = 0;
    pCMe->m_Descriptor.metadata_kv_count = 0;
    pCMe->m_Descriptor.tensor_data_offset = 0;
    pCMe->m_Alignment = ECO_GGUF1_DEFAULT_ALIGNMENT;
    pCMe->m_pIMetadataKVs = 0;
    pCMe->m_pITensorInfos = 0;
    pCMe->m_pITensorData = 0;
    pCMe->m_TensorDataSourcePath = 0;
    pCMe->m_TensorDataSourceOffset = 0;
    pCMe->m_TensorDataSourceSize = 0;

    *ppIFile = (IEcoGGUF1File*)pCMe;
    return 0;
}
