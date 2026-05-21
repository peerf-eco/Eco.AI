#include "CEcoGGUF1MetadataKV.h"
#include "IEcoSystem1.h"
#include "IEcoInterfaceBus1.h"

static uint64_t CEcoGGUF1_MetadataKV_strlen(const char_t* value) {
    uint64_t len = 0;

    if (value == 0) {
        return 0;
    }

    while (value[len] != 0) {
        ++len;
    }

    return len;
}

static void CEcoGGUF1_MetadataKV_copy(char_t* dst, const char_t* src, uint64_t len) {
    uint64_t index = 0;

    if (dst == 0 || src == 0) {
        return;
    }

    for (index = 0; index < len; ++index) {
        dst[index] = src[index];
    }
    dst[len] = 0;
}

int16_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataKV_QueryInterface(IEcoGGUF1MetadataKVPtr_t me, const UGUID* riid, voidptr_t* ppv) {
    if (me == 0 || ppv == 0) {
        return -1;
    }

    if (IsEqualUGUID(riid, &IID_IEcoGGUF1MetadataKV) || IsEqualUGUID(riid, &IID_IEcoUnknown)) {
        *ppv = me;
        me->pVTbl->AddRef(me);
        return 0;
    }

    *ppv = 0;
    return -1;
}

uint32_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataKV_AddRef(IEcoGGUF1MetadataKVPtr_t me) {
    CEcoGGUF1_6EAA44B1MetadataKV* pCMe = (CEcoGGUF1_6EAA44B1MetadataKV*)me;

    if (me == 0) {
        return (uint32_t)-1;
    }

    return ++pCMe->m_cRef;
}

void ECOCALLMETHOD deleteCEcoGGUF1_6EAA44B1MetadataKV(IEcoGGUF1MetadataKV* pIKV) {
    CEcoGGUF1_6EAA44B1MetadataKV* pCMe = (CEcoGGUF1_6EAA44B1MetadataKV*)pIKV;
    IEcoMemoryAllocator1* pIMem = 0;

    if (pCMe == 0) {
        return;
    }

    pIMem = pCMe->m_pIMem;

    if (pCMe->m_Descriptor.key != 0 && pIMem != 0) {
        pIMem->pVTbl->Free(pIMem, pCMe->m_Descriptor.key);
    }

    if (pCMe->m_pIValue != 0) {
        pCMe->m_pIValue->pVTbl->Release(pCMe->m_pIValue);
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

uint32_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataKV_Release(IEcoGGUF1MetadataKVPtr_t me) {
    CEcoGGUF1_6EAA44B1MetadataKV* pCMe = (CEcoGGUF1_6EAA44B1MetadataKV*)me;

    if (me == 0) {
        return (uint32_t)-1;
    }

    --pCMe->m_cRef;
    if (pCMe->m_cRef == 0) {
        deleteCEcoGGUF1_6EAA44B1MetadataKV((IEcoGGUF1MetadataKV*)pCMe);
        return 0;
    }

    return pCMe->m_cRef;
}

ECO_GGUF1_METADATA_KV_DESCRIPTOR* ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataKV_get_Descriptor(IEcoGGUF1MetadataKVPtr_t me) {
    CEcoGGUF1_6EAA44B1MetadataKV* pCMe = (CEcoGGUF1_6EAA44B1MetadataKV*)me;

    return me == 0 ? 0 : &pCMe->m_Descriptor;
}

char_t* ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataKV_get_Key(IEcoGGUF1MetadataKVPtr_t me) {
    CEcoGGUF1_6EAA44B1MetadataKV* pCMe = (CEcoGGUF1_6EAA44B1MetadataKV*)me;

    return me == 0 ? 0 : pCMe->m_Descriptor.key;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataKV_set_KeyBytes(IEcoGGUF1MetadataKVPtr_t me, char_t* key, uint64_t len) {
    CEcoGGUF1_6EAA44B1MetadataKV* pCMe = (CEcoGGUF1_6EAA44B1MetadataKV*)me;
    char_t* pNewKey = 0;

    if (me == 0 || pCMe->m_pIMem == 0) {
        return;
    }

    if (pCMe->m_Descriptor.key != 0) {
        pCMe->m_pIMem->pVTbl->Free(pCMe->m_pIMem, pCMe->m_Descriptor.key);
        pCMe->m_Descriptor.key = 0;
        pCMe->m_Descriptor.key_length = 0;
    }

    if (key == 0) {
        return;
    }

    if (len > (uint64_t)((uint32_t)-1) - 1u) {
        return;
    }

    pNewKey = (char_t*)pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, (uint32_t)(len + 1));
    if (pNewKey == 0) {
        return;
    }

    if (len != 0) {
        CEcoGGUF1_MetadataKV_copy(pNewKey, key, len);
    }
    else {
        pNewKey[0] = 0;
    }
    pCMe->m_Descriptor.key = pNewKey;
    pCMe->m_Descriptor.key_length = len;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataKV_set_Key(IEcoGGUF1MetadataKVPtr_t me, char_t* key) {
    uint64_t len = 0;

    if (me == 0) {
        return;
    }

    len = CEcoGGUF1_MetadataKV_strlen(key);
    me->pVTbl->set_KeyBytes(me, key, len);
}

IEcoGGUF1MetadataValue* ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataKV_get_Value(IEcoGGUF1MetadataKVPtr_t me) {
    CEcoGGUF1_6EAA44B1MetadataKV* pCMe = (CEcoGGUF1_6EAA44B1MetadataKV*)me;

    return me == 0 ? 0 : pCMe->m_pIValue;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataKV_set_Value(IEcoGGUF1MetadataKVPtr_t me, IEcoGGUF1MetadataValue* pIValue) {
    CEcoGGUF1_6EAA44B1MetadataKV* pCMe = (CEcoGGUF1_6EAA44B1MetadataKV*)me;

    if (me == 0) {
        return;
    }

    if (pCMe->m_pIValue != 0) {
        pCMe->m_pIValue->pVTbl->Release(pCMe->m_pIValue);
    }

    pCMe->m_pIValue = pIValue;
    if (pCMe->m_pIValue != 0) {
        pCMe->m_pIValue->pVTbl->AddRef(pCMe->m_pIValue);
        pCMe->m_Descriptor.value_type = pCMe->m_pIValue->pVTbl->get_Descriptor(pCMe->m_pIValue)->value_type;
    }
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataKV_set_Descriptor(IEcoGGUF1MetadataKVPtr_t me, ECO_GGUF1_METADATA_KV_DESCRIPTOR* descriptor) {
    CEcoGGUF1_6EAA44B1MetadataKV* pCMe = (CEcoGGUF1_6EAA44B1MetadataKV*)me;

    if (me == 0 || descriptor == 0) {
        return;
    }

    me->pVTbl->set_KeyBytes(me, descriptor->key, descriptor->key_length);
    pCMe->m_Descriptor.value_type = descriptor->value_type;
}

static IEcoGGUF1MetadataKVVTbl g_xEcoGGUF1MetadataKVVTbl = {
    CEcoGGUF1_6EAA44B1MetadataKV_QueryInterface,
    CEcoGGUF1_6EAA44B1MetadataKV_AddRef,
    CEcoGGUF1_6EAA44B1MetadataKV_Release,
    CEcoGGUF1_6EAA44B1MetadataKV_get_Descriptor,
    CEcoGGUF1_6EAA44B1MetadataKV_set_Descriptor,
    CEcoGGUF1_6EAA44B1MetadataKV_get_Key,
    CEcoGGUF1_6EAA44B1MetadataKV_set_Key,
    CEcoGGUF1_6EAA44B1MetadataKV_get_Value,
    CEcoGGUF1_6EAA44B1MetadataKV_set_Value,
    CEcoGGUF1_6EAA44B1MetadataKV_set_KeyBytes
};

int16_t ECOCALLMETHOD createCEcoGGUF1_6EAA44B1MetadataKV(IEcoUnknown* pIUnkSystem, IEcoUnknown* pIUnkOuter, IEcoGGUF1MetadataKV** ppIKV) {
    IEcoSystem1* pISys = 0;
    IEcoInterfaceBus1* pIBus = 0;
    IEcoMemoryAllocator1* pIMem = 0;
    IEcoString1* pIStr = 0;
    CEcoGGUF1_6EAA44B1MetadataKV* pCMe = 0;
    int16_t result = -1;

    (void)pIUnkOuter;

    if (ppIKV == 0 || pIUnkSystem == 0) {
        return -1;
    }

    *ppIKV = 0;

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

    pCMe = (CEcoGGUF1_6EAA44B1MetadataKV*)pIMem->pVTbl->Alloc(pIMem, sizeof(CEcoGGUF1_6EAA44B1MetadataKV));
    if (pCMe == 0) {
        if (pIStr != 0) {
            pIStr->pVTbl->Release(pIStr);
        }
        pIMem->pVTbl->Release(pIMem);
        pISys->pVTbl->Release(pISys);
        return -1;
    }

    pCMe->m_pVTblIMetadataKV = &g_xEcoGGUF1MetadataKVVTbl;
    pCMe->m_cRef = 1;
    pCMe->m_pIMem = pIMem;
    pCMe->m_pISys = pISys;
    pCMe->m_pIStr = pIStr;
    pCMe->m_pIValue = 0;
    pCMe->m_Descriptor.key_length = 0;
    pCMe->m_Descriptor.key = 0;
    pCMe->m_Descriptor.value_type = ECO_GGUF1_METADATA_VALUE_TYPE_UINT8;

    *ppIKV = (IEcoGGUF1MetadataKV*)pCMe;
    return 0;
}
