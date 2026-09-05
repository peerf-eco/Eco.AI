#include "CEcoGGUF1MetadataValue.h"
#include "IEcoSystem1.h"
#include "IEcoInterfaceBus1.h"

static uint64_t CEcoGGUF1_MetadataValue_strlen(const char_t* value) {
    uint64_t len = 0;

    if (value == 0) {
        return 0;
    }

    while (value[len] != 0) {
        ++len;
    }

    return len;
}

static void CEcoGGUF1_MetadataValue_copy(char_t* dst, const char_t* src, uint64_t len) {
    uint64_t index = 0;

    if (dst == 0 || src == 0) {
        return;
    }

    for (index = 0; index < len; ++index) {
        dst[index] = src[index];
    }
    dst[len] = 0;
}

int16_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataValue_QueryInterface(IEcoGGUF1MetadataValuePtr_t me, const UGUID* riid, voidptr_t* ppv) {
    if (me == 0 || ppv == 0) {
        return -1;
    }

    if (IsEqualUGUID(riid, &IID_IEcoGGUF1MetadataValue) || IsEqualUGUID(riid, &IID_IEcoUnknown)) {
        *ppv = me;
        me->pVTbl->AddRef(me);
        return 0;
    }

    *ppv = 0;
    return -1;
}

uint32_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataValue_AddRef(IEcoGGUF1MetadataValuePtr_t me) {
    CEcoGGUF1_6EAA44B1MetadataValue* pCMe = (CEcoGGUF1_6EAA44B1MetadataValue*)me;

    if (me == 0) {
        return (uint32_t)-1;
    }

    return ++pCMe->m_cRef;
}

void ECOCALLMETHOD deleteCEcoGGUF1_6EAA44B1MetadataValue(IEcoGGUF1MetadataValue* pIValue) {
    CEcoGGUF1_6EAA44B1MetadataValue* pCMe = (CEcoGGUF1_6EAA44B1MetadataValue*)pIValue;
    IEcoMemoryAllocator1* pIMem = 0;

    if (pCMe == 0) {
        return;
    }

    pIMem = pCMe->m_pIMem;

    if (pCMe->m_Descriptor.string.string != 0 && pIMem != 0) {
        pIMem->pVTbl->Free(pIMem, pCMe->m_Descriptor.string.string);
    }

    if (pCMe->m_pIArrayItems != 0) {
        pCMe->m_pIArrayItems->pVTbl->Release(pCMe->m_pIArrayItems);
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

uint32_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataValue_Release(IEcoGGUF1MetadataValuePtr_t me) {
    CEcoGGUF1_6EAA44B1MetadataValue* pCMe = (CEcoGGUF1_6EAA44B1MetadataValue*)me;

    if (me == 0) {
        return (uint32_t)-1;
    }

    --pCMe->m_cRef;
    if (pCMe->m_cRef == 0) {
        deleteCEcoGGUF1_6EAA44B1MetadataValue((IEcoGGUF1MetadataValue*)pCMe);
        return 0;
    }

    return pCMe->m_cRef;
}

ECO_GGUF1_METADATA_VALUE_DESCRIPTOR* ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataValue_get_Descriptor(IEcoGGUF1MetadataValuePtr_t me) {
    CEcoGGUF1_6EAA44B1MetadataValue* pCMe = (CEcoGGUF1_6EAA44B1MetadataValue*)me;

    return me == 0 ? 0 : &pCMe->m_Descriptor;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataValue_set_StringBytes(IEcoGGUF1MetadataValuePtr_t me, char_t* value, uint64_t len) {
    CEcoGGUF1_6EAA44B1MetadataValue* pCMe = (CEcoGGUF1_6EAA44B1MetadataValue*)me;
    char_t* pNewValue = 0;

    if (me == 0 || pCMe->m_pIMem == 0) {
        return;
    }

    if (pCMe->m_Descriptor.string.string != 0) {
        pCMe->m_pIMem->pVTbl->Free(pCMe->m_pIMem, pCMe->m_Descriptor.string.string);
        pCMe->m_Descriptor.string.string = 0;
        pCMe->m_Descriptor.string.len = 0;
    }

    if (value == 0) {
        return;
    }

    if (len > (uint64_t)((uint32_t)-1) - 1u) {
        return;
    }

    pNewValue = (char_t*)pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, (uint32_t)(len + 1));
    if (pNewValue == 0) {
        return;
    }

    if (len != 0) {
        CEcoGGUF1_MetadataValue_copy(pNewValue, value, len);
    }
    else {
        pNewValue[0] = 0;
    }
    pCMe->m_Descriptor.string.string = pNewValue;
    pCMe->m_Descriptor.string.len = len;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataValue_set_String(IEcoGGUF1MetadataValuePtr_t me, char_t* value) {
    uint64_t len = 0;

    if (me == 0) {
        return;
    }

    len = CEcoGGUF1_MetadataValue_strlen(value);
    me->pVTbl->set_StringBytes(me, value, len);
}

char_t* ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataValue_get_String(IEcoGGUF1MetadataValuePtr_t me) {
    CEcoGGUF1_6EAA44B1MetadataValue* pCMe = (CEcoGGUF1_6EAA44B1MetadataValue*)me;

    return me == 0 ? 0 : pCMe->m_Descriptor.string.string;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataValue_set_Descriptor(IEcoGGUF1MetadataValuePtr_t me, ECO_GGUF1_METADATA_VALUE_DESCRIPTOR* descriptor) {
    CEcoGGUF1_6EAA44B1MetadataValue* pCMe = (CEcoGGUF1_6EAA44B1MetadataValue*)me;

    if (me == 0 || descriptor == 0) {
        return;
    }

    pCMe->m_Descriptor.value_type = descriptor->value_type;
    pCMe->m_Descriptor.uint8_value = descriptor->uint8_value;
    pCMe->m_Descriptor.int8_value = descriptor->int8_value;
    pCMe->m_Descriptor.uint16_value = descriptor->uint16_value;
    pCMe->m_Descriptor.int16_value = descriptor->int16_value;
    pCMe->m_Descriptor.uint32_value = descriptor->uint32_value;
    pCMe->m_Descriptor.int32_value = descriptor->int32_value;
    pCMe->m_Descriptor.float32_value = descriptor->float32_value;
    pCMe->m_Descriptor.uint64_value = descriptor->uint64_value;
    pCMe->m_Descriptor.int64_value = descriptor->int64_value;
    pCMe->m_Descriptor.float64_value = descriptor->float64_value;
    pCMe->m_Descriptor.bool_value = descriptor->bool_value;
    pCMe->m_Descriptor.array.type = descriptor->array.type;
    pCMe->m_Descriptor.array.len = descriptor->array.len;

    me->pVTbl->set_StringBytes(me, descriptor->string.string, descriptor->string.len);
}

IEcoList1* ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataValue_get_ArrayItems(IEcoGGUF1MetadataValuePtr_t me) {
    CEcoGGUF1_6EAA44B1MetadataValue* pCMe = (CEcoGGUF1_6EAA44B1MetadataValue*)me;

    return me == 0 ? 0 : pCMe->m_pIArrayItems;
}

void ECOCALLMETHOD CEcoGGUF1_6EAA44B1MetadataValue_set_ArrayItems(IEcoGGUF1MetadataValuePtr_t me, IEcoList1* pIItems) {
    CEcoGGUF1_6EAA44B1MetadataValue* pCMe = (CEcoGGUF1_6EAA44B1MetadataValue*)me;

    if (me == 0) {
        return;
    }

    if (pCMe->m_pIArrayItems != 0) {
        pCMe->m_pIArrayItems->pVTbl->Release(pCMe->m_pIArrayItems);
    }

    pCMe->m_pIArrayItems = pIItems;
    if (pCMe->m_pIArrayItems != 0) {
        pCMe->m_pIArrayItems->pVTbl->AddRef(pCMe->m_pIArrayItems);
        pCMe->m_Descriptor.array.len = pCMe->m_pIArrayItems->pVTbl->Count(pCMe->m_pIArrayItems);
    }
    else {
        pCMe->m_Descriptor.array.len = 0;
    }
}

static IEcoGGUF1MetadataValueVTbl g_xEcoGGUF1MetadataValueVTbl = {
    CEcoGGUF1_6EAA44B1MetadataValue_QueryInterface,
    CEcoGGUF1_6EAA44B1MetadataValue_AddRef,
    CEcoGGUF1_6EAA44B1MetadataValue_Release,
    CEcoGGUF1_6EAA44B1MetadataValue_get_Descriptor,
    CEcoGGUF1_6EAA44B1MetadataValue_set_Descriptor,
    CEcoGGUF1_6EAA44B1MetadataValue_get_ArrayItems,
    CEcoGGUF1_6EAA44B1MetadataValue_set_ArrayItems,
    CEcoGGUF1_6EAA44B1MetadataValue_get_String,
    CEcoGGUF1_6EAA44B1MetadataValue_set_String,
    CEcoGGUF1_6EAA44B1MetadataValue_set_StringBytes
};

int16_t ECOCALLMETHOD createCEcoGGUF1_6EAA44B1MetadataValue(IEcoUnknown* pIUnkSystem, IEcoUnknown* pIUnkOuter, IEcoGGUF1MetadataValue** ppIValue) {
    IEcoSystem1* pISys = 0;
    IEcoInterfaceBus1* pIBus = 0;
    IEcoMemoryAllocator1* pIMem = 0;
    IEcoString1* pIStr = 0;
    CEcoGGUF1_6EAA44B1MetadataValue* pCMe = 0;
    int16_t result = -1;

    (void)pIUnkOuter;

    if (ppIValue == 0 || pIUnkSystem == 0) {
        return -1;
    }

    *ppIValue = 0;

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

    pCMe = (CEcoGGUF1_6EAA44B1MetadataValue*)pIMem->pVTbl->Alloc(pIMem, sizeof(CEcoGGUF1_6EAA44B1MetadataValue));
    if (pCMe == 0) {
        if (pIStr != 0) {
            pIStr->pVTbl->Release(pIStr);
        }
        pIMem->pVTbl->Release(pIMem);
        pISys->pVTbl->Release(pISys);
        return -1;
    }

    pCMe->m_pVTblIMetadataValue = &g_xEcoGGUF1MetadataValueVTbl;
    pCMe->m_cRef = 1;
    pCMe->m_pIMem = pIMem;
    pCMe->m_pISys = pISys;
    pCMe->m_pIStr = pIStr;
    pCMe->m_pIArrayItems = 0;
    pCMe->m_Descriptor.value_type = ECO_GGUF1_METADATA_VALUE_TYPE_UINT8;
    pCMe->m_Descriptor.uint8_value = 0;
    pCMe->m_Descriptor.int8_value = 0;
    pCMe->m_Descriptor.uint16_value = 0;
    pCMe->m_Descriptor.int16_value = 0;
    pCMe->m_Descriptor.uint32_value = 0;
    pCMe->m_Descriptor.int32_value = 0;
    pCMe->m_Descriptor.float32_value = 0.0f;
    pCMe->m_Descriptor.uint64_value = 0;
    pCMe->m_Descriptor.int64_value = 0;
    pCMe->m_Descriptor.float64_value = 0.0;
    pCMe->m_Descriptor.bool_value = 0;
    pCMe->m_Descriptor.string.len = 0;
    pCMe->m_Descriptor.string.string = 0;
    pCMe->m_Descriptor.array.type = ECO_GGUF1_METADATA_VALUE_TYPE_UINT8;
    pCMe->m_Descriptor.array.len = 0;

    *ppIValue = (IEcoGGUF1MetadataValue*)pCMe;
    return 0;
}
