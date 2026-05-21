#include "IEcoSystem1.h"
#include "IEcoInterfaceBus1.h"
#include "IdEcoList1.h"
#include "CEcoGGUF1.h"
#include "CEcoGGUF1File.h"
#include "CEcoGGUF1TensorInfo.h"
#include "CEcoGGUF1MetadataKV.h"
#include "CEcoGGUF1MetadataValue.h"
#include "CEcoGGUF1RawData.h"
#include "ErrEcoGGUF1.h"
#include "gguf.h"

#include <inttypes.h>
#include <limits.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

gguf_status gguf_serialized_size(const gguf_file_t* file, uint64_t* size, char* error, size_t error_size);

static void CEcoGGUF1_set_error(char_t* error, size_t error_size, const char_t* format, ...) {
    va_list args;

    if (error == 0 || error_size == 0) {
        return;
    }

    va_start(args, format);
    vsnprintf(error, error_size, format, args);
    va_end(args);
}

static int16_t CEcoGGUF1_map_status(gguf_status status) {
    switch (status) {
        case GGUF_STATUS_OK:
            return ECO_E_GGUF1_OK;
        case GGUF_STATUS_INVALID_ARGUMENT:
            return ECO_E_GGUF1_INVALID_ARGUMENT;
        case GGUF_STATUS_OUT_OF_MEMORY:
            return ECO_E_GGUF1_OUT_OF_MEMORY;
        case GGUF_STATUS_INVALID_MAGIC:
            return ECO_E_GGUF1_INVALID_MAGIC;
        case GGUF_STATUS_UNSUPPORTED_VERSION:
            return ECO_E_GGUF1_UNSUPPORTED_VERSION;
        default:
            return ECO_E_GGUF1_FAIL;
    }
}

static IEcoList1* CEcoGGUF1_createList(CEcoGGUF1_6EAA44B1* pCMe) {
    IEcoList1* pIList = 0;

    if (pCMe == 0 || pCMe->m_pIBus == 0) {
        return 0;
    }

    if (pCMe->m_pIBus->pVTbl->QueryComponent(pCMe->m_pIBus, &CID_EcoList1, 0, &IID_IEcoList1, (void**)&pIList) != 0) {
        return 0;
    }

    return pIList;
}

static IEcoRawData1* CEcoGGUF1_createRawDataFromBytes(IEcoGGUF1Ptr_t me, const uint8_t* data, uint64_t size) {
    IEcoRawData1* pIRawData = 0;
    byte_t* pPointer = 0;

    if (me == 0 || size > UINT32_MAX) {
        return 0;
    }

    pIRawData = me->pVTbl->createRawData(me);
    if (pIRawData == 0) {
        return 0;
    }

    if (size == 0) {
        return pIRawData;
    }

    pPointer = pIRawData->pVTbl->Alloc(pIRawData, (uint32_t)size);
    if (pPointer == 0) {
        pIRawData->pVTbl->Release(pIRawData);
        return 0;
    }

    memcpy(pPointer, data, (size_t)size);
    return pIRawData;
}

static int16_t CEcoGGUF1_queryRawData(IEcoUnknown* pIUnknown, IEcoRawData1** ppIRawData) {
    if (ppIRawData == 0) {
        return ECO_E_GGUF1_INVALID_ARGUMENT;
    }

    *ppIRawData = 0;
    if (pIUnknown == 0) {
        return ECO_E_GGUF1_OK;
    }

    if (pIUnknown->pVTbl->QueryInterface(pIUnknown, &IID_IEcoRawData1, (void**)ppIRawData) != 0) {
        return ECO_E_GGUF1_FAIL;
    }

    return ECO_E_GGUF1_OK;
}

static int16_t CEcoGGUF1_alloc_gguf_string(const char_t* value, uint64_t len, gguf_string_t* out_string, char_t* error, size_t error_size) {
    if (out_string == 0) {
        CEcoGGUF1_set_error(error, error_size, "Invalid GGUF string output");
        return ECO_E_GGUF1_INVALID_ARGUMENT;
    }

    out_string->len = 0;
    out_string->string = 0;

    if (value == 0) {
        if (len != 0) {
            CEcoGGUF1_set_error(error, error_size, "String length is non-zero but pointer is null");
            return ECO_E_GGUF1_FAIL;
        }
        return ECO_E_GGUF1_OK;
    }

    if (len > (uint64_t)((size_t)-1) - 1u) {
        CEcoGGUF1_set_error(error, error_size, "String is too large to allocate");
        return ECO_E_GGUF1_OUT_OF_MEMORY;
    }

    out_string->string = (char*)malloc((size_t)len + 1u);
    if (out_string->string == 0) {
        CEcoGGUF1_set_error(error, error_size, "Out of memory allocating string");
        return ECO_E_GGUF1_OUT_OF_MEMORY;
    }

    memcpy(out_string->string, value, (size_t)len);
    out_string->string[len] = 0;
    out_string->len = len;
    return ECO_E_GGUF1_OK;
}

static int16_t CEcoGGUF1_alloc_c_string(const char_t* value, char** out_string, char_t* error, size_t error_size) {
    uint64_t len = 0;

    if (out_string == 0) {
        return ECO_E_GGUF1_INVALID_ARGUMENT;
    }

    *out_string = 0;
    if (value == 0) {
        return ECO_E_GGUF1_OK;
    }

    while (value[len] != 0) {
        ++len;
    }

    if (len > (uint64_t)((size_t)-1) - 1u) {
        CEcoGGUF1_set_error(error, error_size, "String is too large to allocate");
        return ECO_E_GGUF1_OUT_OF_MEMORY;
    }

    *out_string = (char*)malloc((size_t)len + 1u);
    if (*out_string == 0) {
        CEcoGGUF1_set_error(error, error_size, "Out of memory allocating string");
        return ECO_E_GGUF1_OUT_OF_MEMORY;
    }

    memcpy(*out_string, value, (size_t)len);
    (*out_string)[len] = 0;
    return ECO_E_GGUF1_OK;
}

static int16_t CEcoGGUF1_fillEcoValueFromGGUF(IEcoGGUF1Ptr_t me, IEcoGGUF1MetadataValue* pIValue, const gguf_metadata_value_t* pSource) {
    CEcoGGUF1_6EAA44B1* pCMe = (CEcoGGUF1_6EAA44B1*)me;
    ECO_GGUF1_METADATA_VALUE_DESCRIPTOR* pDescriptor = 0;
    IEcoList1* pIItems = 0;
    uint64_t index = 0;

    if (me == 0 || pIValue == 0 || pSource == 0) {
        return ECO_E_GGUF1_INVALID_ARGUMENT;
    }

    pDescriptor = pIValue->pVTbl->get_Descriptor(pIValue);
    if (pDescriptor == 0) {
        return ECO_E_GGUF1_FAIL;
    }

    pDescriptor->value_type = pSource->type;
    switch (pSource->type) {
        case GGUF_METADATA_VALUE_TYPE_UINT8:
            pDescriptor->uint8_value = pSource->value.uint8;
            break;
        case GGUF_METADATA_VALUE_TYPE_INT8:
            pDescriptor->int8_value = pSource->value.int8;
            break;
        case GGUF_METADATA_VALUE_TYPE_UINT16:
            pDescriptor->uint16_value = pSource->value.uint16;
            break;
        case GGUF_METADATA_VALUE_TYPE_INT16:
            pDescriptor->int16_value = pSource->value.int16;
            break;
        case GGUF_METADATA_VALUE_TYPE_UINT32:
            pDescriptor->uint32_value = pSource->value.uint32;
            break;
        case GGUF_METADATA_VALUE_TYPE_INT32:
            pDescriptor->int32_value = pSource->value.int32;
            break;
        case GGUF_METADATA_VALUE_TYPE_FLOAT32:
            pDescriptor->float32_value = pSource->value.float32;
            break;
        case GGUF_METADATA_VALUE_TYPE_BOOL:
            pDescriptor->bool_value = pSource->value.bool_ ? 1 : 0;
            break;
        case GGUF_METADATA_VALUE_TYPE_STRING:
            pIValue->pVTbl->set_StringBytes(pIValue, (char_t*)pSource->value.string.string, pSource->value.string.len);
            break;
        case GGUF_METADATA_VALUE_TYPE_ARRAY:
            pDescriptor->array.type = pSource->value.array.type;
            pDescriptor->array.len = pSource->value.array.len;
            if (pSource->value.array.len != 0) {
                pIItems = CEcoGGUF1_createList(pCMe);
                if (pIItems == 0) {
                    return ECO_E_GGUF1_OUT_OF_MEMORY;
                }
            }
            for (index = 0; index < pSource->value.array.len; ++index) {
                IEcoGGUF1MetadataValue* pIChild = me->pVTbl->createMetadataValue(me);

                if (pIChild == 0) {
                    if (pIItems != 0) {
                        pIItems->pVTbl->Release(pIItems);
                    }
                    return ECO_E_GGUF1_OUT_OF_MEMORY;
                }

                if (CEcoGGUF1_fillEcoValueFromGGUF(me, pIChild, &pSource->value.array.items[index]) != ECO_E_GGUF1_OK) {
                    pIChild->pVTbl->Release(pIChild);
                    if (pIItems != 0) {
                        pIItems->pVTbl->Release(pIItems);
                    }
                    return ECO_E_GGUF1_FAIL;
                }

                pIItems->pVTbl->Add(pIItems, pIChild);
                pIChild->pVTbl->Release(pIChild);
            }
            pIValue->pVTbl->set_ArrayItems(pIValue, pIItems);
            if (pIItems != 0) {
                pIItems->pVTbl->Release(pIItems);
            }
            break;
        case GGUF_METADATA_VALUE_TYPE_UINT64:
            pDescriptor->uint64_value = pSource->value.uint64;
            break;
        case GGUF_METADATA_VALUE_TYPE_INT64:
            pDescriptor->int64_value = pSource->value.int64;
            break;
        case GGUF_METADATA_VALUE_TYPE_FLOAT64:
            pDescriptor->float64_value = pSource->value.float64;
            break;
        default:
            return ECO_E_GGUF1_FAIL;
    }

    return ECO_E_GGUF1_OK;
}

static int16_t CEcoGGUF1_convertGGUFToEcoFile(IEcoGGUF1Ptr_t me, const gguf_file_t* pSource, IEcoGGUF1File** ppIFile) {
    IEcoGGUF1File* pIFile = 0;
    ECO_GGUF1_HEADER_DESCRIPTOR* pHeader = 0;
    CEcoGGUF1_6EAA44B1* pCMe = (CEcoGGUF1_6EAA44B1*)me;
    IEcoList1* pIMetadata = 0;
    IEcoList1* pITensors = 0;
    IEcoRawData1* pIFileRawData = 0;
    uint64_t index = 0;

    if (ppIFile == 0 || me == 0 || pSource == 0) {
        return ECO_E_GGUF1_INVALID_ARGUMENT;
    }

    *ppIFile = 0;

    pIFile = me->pVTbl->createFile(me);
    if (pIFile == 0) {
        return ECO_E_GGUF1_OUT_OF_MEMORY;
    }

    pHeader = pIFile->pVTbl->get_Descriptor(pIFile);
    pHeader->magic = pSource->header.magic;
    pHeader->version = pSource->header.version;
    pHeader->tensor_count = pSource->header.tensor_count;
    pHeader->metadata_kv_count = pSource->header.metadata_kv_count;
    pHeader->tensor_data_offset = pSource->tensor_data_offset;
    pIFile->pVTbl->set_Alignment(pIFile, pSource->alignment);
    if (pSource->tensor_data_source_path != 0) {
        pIFile->pVTbl->set_TensorDataSource(pIFile,
                                            (char_t*)pSource->tensor_data_source_path,
                                            pSource->tensor_data_source_offset,
                                            pSource->tensor_data_source_size);
    }

    if (pSource->header.metadata_kv_count != 0) {
        pIMetadata = CEcoGGUF1_createList(pCMe);
        if (pIMetadata == 0) {
            pIFile->pVTbl->Release(pIFile);
            return ECO_E_GGUF1_OUT_OF_MEMORY;
        }
    }

    for (index = 0; index < pSource->header.metadata_kv_count; ++index) {
        IEcoGGUF1MetadataKV* pIKV = me->pVTbl->createMetadataKV(me);
        IEcoGGUF1MetadataValue* pIValue = 0;

        if (pIKV == 0) {
            if (pIMetadata != 0) {
                pIMetadata->pVTbl->Release(pIMetadata);
            }
            pIFile->pVTbl->Release(pIFile);
            return ECO_E_GGUF1_OUT_OF_MEMORY;
        }

        pIKV->pVTbl->set_KeyBytes(pIKV,
                                  (char_t*)pSource->metadata_kv[index].key.string,
                                  pSource->metadata_kv[index].key.len);

        pIValue = me->pVTbl->createMetadataValue(me);
        if (pIValue == 0 || CEcoGGUF1_fillEcoValueFromGGUF(me, pIValue, &pSource->metadata_kv[index].value) != ECO_E_GGUF1_OK) {
            if (pIValue != 0) {
                pIValue->pVTbl->Release(pIValue);
            }
            pIKV->pVTbl->Release(pIKV);
            if (pIMetadata != 0) {
                pIMetadata->pVTbl->Release(pIMetadata);
            }
            pIFile->pVTbl->Release(pIFile);
            return ECO_E_GGUF1_FAIL;
        }

        pIKV->pVTbl->set_Value(pIKV, pIValue);
        pIValue->pVTbl->Release(pIValue);
        pIMetadata->pVTbl->Add(pIMetadata, pIKV);
        pIKV->pVTbl->Release(pIKV);
    }

    if (pIMetadata != 0) {
        pIFile->pVTbl->set_MetadataKVs(pIFile, pIMetadata);
        pIMetadata->pVTbl->Release(pIMetadata);
    }

    if (pSource->header.tensor_count != 0) {
        pITensors = CEcoGGUF1_createList(pCMe);
        if (pITensors == 0) {
            pIFile->pVTbl->Release(pIFile);
            return ECO_E_GGUF1_OUT_OF_MEMORY;
        }
    }

    for (index = 0; index < pSource->header.tensor_count; ++index) {
        IEcoGGUF1TensorInfo* pITensor = me->pVTbl->createTensorInfo(me);
        ECO_GGUF1_TENSOR_INFO_DESCRIPTOR* pTensorDescriptor = 0;
        IEcoRawData1* pITensorRawData = 0;
        uint32_t dim_index = 0;

        if (pITensor == 0) {
            if (pITensors != 0) {
                pITensors->pVTbl->Release(pITensors);
            }
            pIFile->pVTbl->Release(pIFile);
            return ECO_E_GGUF1_OUT_OF_MEMORY;
        }

        if (pSource->tensor_infos[index].n_dimensions > ECO_GGUF1_MAX_DIMS ||
            (pSource->tensor_infos[index].data != 0 && pSource->tensor_infos[index].size > UINT32_MAX)) {
            pITensor->pVTbl->Release(pITensor);
            if (pITensors != 0) {
                pITensors->pVTbl->Release(pITensors);
            }
            pIFile->pVTbl->Release(pIFile);
            return ECO_E_GGUF1_FAIL;
        }

        pITensor->pVTbl->set_Name(pITensor, (char_t*)pSource->tensor_infos[index].name.string);
        pTensorDescriptor = pITensor->pVTbl->get_Descriptor(pITensor);
        pTensorDescriptor->n_dimensions = pSource->tensor_infos[index].n_dimensions;
        pTensorDescriptor->type = pSource->tensor_infos[index].type;
        pTensorDescriptor->offset = pSource->tensor_infos[index].offset;
        for (dim_index = 0; dim_index < pTensorDescriptor->n_dimensions; ++dim_index) {
            pTensorDescriptor->dimensions[dim_index] = pSource->tensor_infos[index].dimensions[dim_index];
        }

        if (pSource->tensor_infos[index].data != 0) {
            pITensorRawData = CEcoGGUF1_createRawDataFromBytes(me, pSource->tensor_infos[index].data, pSource->tensor_infos[index].size);
        }
        if (pSource->tensor_infos[index].data != 0 && pSource->tensor_infos[index].size != 0 && pITensorRawData == 0) {
            pITensor->pVTbl->Release(pITensor);
            if (pITensors != 0) {
                pITensors->pVTbl->Release(pITensors);
            }
            pIFile->pVTbl->Release(pIFile);
            return ECO_E_GGUF1_OUT_OF_MEMORY;
        }

        if (pITensorRawData != 0) {
            pITensor->pVTbl->set_RawData(pITensor, (IEcoUnknown*)pITensorRawData);
            pITensorRawData->pVTbl->Release(pITensorRawData);
        }

        pITensors->pVTbl->Add(pITensors, pITensor);
        pITensor->pVTbl->Release(pITensor);
    }

    if (pITensors != 0) {
        pIFile->pVTbl->set_TensorInfos(pIFile, pITensors);
        pITensors->pVTbl->Release(pITensors);
    }

    if (pSource->tensor_data != 0) {
        if (pSource->tensor_data_size > UINT32_MAX) {
            pIFile->pVTbl->Release(pIFile);
            return ECO_E_GGUF1_OUT_OF_MEMORY;
        }
        pIFileRawData = CEcoGGUF1_createRawDataFromBytes(me, pSource->tensor_data, pSource->tensor_data_size);
        if (pSource->tensor_data_size != 0 && pIFileRawData == 0) {
            pIFile->pVTbl->Release(pIFile);
            return ECO_E_GGUF1_OUT_OF_MEMORY;
        }
    }

    if (pIFileRawData != 0) {
        pIFile->pVTbl->set_TensorData(pIFile, (IEcoUnknown*)pIFileRawData);
        pIFileRawData->pVTbl->Release(pIFileRawData);
    }

    *ppIFile = pIFile;
    return ECO_E_GGUF1_OK;
}

static int16_t CEcoGGUF1_convertEcoValueToGGUF(IEcoGGUF1MetadataValue* pIValue, gguf_metadata_value_t* pValue, char_t* error, size_t error_size) {
    ECO_GGUF1_METADATA_VALUE_DESCRIPTOR* pDescriptor = 0;
    IEcoList1* pIItems = 0;
    uint64_t index = 0;

    if (pIValue == 0 || pValue == 0) {
        return ECO_E_GGUF1_INVALID_ARGUMENT;
    }

    memset(pValue, 0, sizeof(*pValue));
    pDescriptor = pIValue->pVTbl->get_Descriptor(pIValue);
    if (pDescriptor == 0) {
        return ECO_E_GGUF1_FAIL;
    }

    pValue->type = pDescriptor->value_type;
    switch (pDescriptor->value_type) {
        case ECO_GGUF1_METADATA_VALUE_TYPE_UINT8:
            pValue->value.uint8 = pDescriptor->uint8_value;
            break;
        case ECO_GGUF1_METADATA_VALUE_TYPE_INT8:
            pValue->value.int8 = pDescriptor->int8_value;
            break;
        case ECO_GGUF1_METADATA_VALUE_TYPE_UINT16:
            pValue->value.uint16 = pDescriptor->uint16_value;
            break;
        case ECO_GGUF1_METADATA_VALUE_TYPE_INT16:
            pValue->value.int16 = pDescriptor->int16_value;
            break;
        case ECO_GGUF1_METADATA_VALUE_TYPE_UINT32:
            pValue->value.uint32 = pDescriptor->uint32_value;
            break;
        case ECO_GGUF1_METADATA_VALUE_TYPE_INT32:
            pValue->value.int32 = pDescriptor->int32_value;
            break;
        case ECO_GGUF1_METADATA_VALUE_TYPE_FLOAT32:
            pValue->value.float32 = pDescriptor->float32_value;
            break;
        case ECO_GGUF1_METADATA_VALUE_TYPE_BOOL:
            pValue->value.bool_ = pDescriptor->bool_value != 0;
            break;
        case ECO_GGUF1_METADATA_VALUE_TYPE_STRING:
            return CEcoGGUF1_alloc_gguf_string(pDescriptor->string.string, pDescriptor->string.len, &pValue->value.string, error, error_size);
        case ECO_GGUF1_METADATA_VALUE_TYPE_ARRAY:
            pIItems = pIValue->pVTbl->get_ArrayItems(pIValue);
            pValue->value.array.type = pDescriptor->array.type;
            pValue->value.array.len = pIItems == 0 ? 0 : pIItems->pVTbl->Count(pIItems);
            if (pValue->value.array.len == 0) {
                pValue->value.array.items = 0;
                break;
            }
            if (pIItems == 0 || pValue->value.array.len > (uint64_t)((size_t)-1) / sizeof(gguf_metadata_value_t)) {
                CEcoGGUF1_set_error(error, error_size, "Invalid metadata array");
                return ECO_E_GGUF1_FAIL;
            }
            pValue->value.array.items = (gguf_metadata_value_t*)calloc((size_t)pValue->value.array.len, sizeof(gguf_metadata_value_t));
            if (pValue->value.array.items == 0) {
                CEcoGGUF1_set_error(error, error_size, "Out of memory allocating metadata array");
                return ECO_E_GGUF1_OUT_OF_MEMORY;
            }
            for (index = 0; index < pValue->value.array.len; ++index) {
                IEcoGGUF1MetadataValue* pIItem = (IEcoGGUF1MetadataValue*)pIItems->pVTbl->Item(pIItems, (uint32_t)index);
                int16_t result = ECO_E_GGUF1_OK;

                if (pIItem == 0) {
                    CEcoGGUF1_set_error(error, error_size, "Null metadata array item at index %" PRIu64, index);
                    return ECO_E_GGUF1_FAIL;
                }

                result = CEcoGGUF1_convertEcoValueToGGUF(pIItem, &pValue->value.array.items[index], error, error_size);
                if (result != ECO_E_GGUF1_OK) {
                    return result;
                }

                if (pValue->value.array.items[index].type != pValue->value.array.type) {
                    CEcoGGUF1_set_error(error, error_size, "Metadata array item type mismatch at index %" PRIu64, index);
                    return ECO_E_GGUF1_FAIL;
                }
            }
            break;
        case ECO_GGUF1_METADATA_VALUE_TYPE_UINT64:
            pValue->value.uint64 = pDescriptor->uint64_value;
            break;
        case ECO_GGUF1_METADATA_VALUE_TYPE_INT64:
            pValue->value.int64 = pDescriptor->int64_value;
            break;
        case ECO_GGUF1_METADATA_VALUE_TYPE_FLOAT64:
            pValue->value.float64 = pDescriptor->float64_value;
            break;
        default:
            CEcoGGUF1_set_error(error, error_size, "Unsupported metadata value type %u", pDescriptor->value_type);
            return ECO_E_GGUF1_FAIL;
    }

    return ECO_E_GGUF1_OK;
}

static int16_t CEcoGGUF1_copyRawDataObject(IEcoUnknown* pIUnknown, uint8_t** ppData, uint64_t* pSize, char_t* error, size_t error_size) {
    IEcoRawData1* pIRawData = 0;
    byte_t* pPointer = 0;
    int16_t result = ECO_E_GGUF1_OK;

    if (ppData == 0 || pSize == 0) {
        return ECO_E_GGUF1_INVALID_ARGUMENT;
    }

    *ppData = 0;
    *pSize = 0;

    result = CEcoGGUF1_queryRawData(pIUnknown, &pIRawData);
    if (result != ECO_E_GGUF1_OK || pIRawData == 0) {
        if (result == ECO_E_GGUF1_OK) {
            return ECO_E_GGUF1_OK;
        }
        CEcoGGUF1_set_error(error, error_size, "Unable to query IEcoRawData1");
        return result;
    }

    *pSize = pIRawData->pVTbl->get_Size(pIRawData);
    if (*pSize != 0) {
        *ppData = (uint8_t*)malloc((size_t)(*pSize));
        if (*ppData == 0) {
            pIRawData->pVTbl->Release(pIRawData);
            CEcoGGUF1_set_error(error, error_size, "Out of memory copying raw data");
            return ECO_E_GGUF1_OUT_OF_MEMORY;
        }

        pPointer = pIRawData->pVTbl->get_Pointer(pIRawData, 0);
        if (pPointer == 0) {
            free(*ppData);
            *ppData = 0;
            *pSize = 0;
            pIRawData->pVTbl->Release(pIRawData);
            CEcoGGUF1_set_error(error, error_size, "Invalid raw data pointer");
            return ECO_E_GGUF1_FAIL;
        }

        memcpy(*ppData, pPointer, (size_t)(*pSize));
    }

    pIRawData->pVTbl->Release(pIRawData);
    return ECO_E_GGUF1_OK;
}

static int16_t CEcoGGUF1_buildTensorDataFromSections(IEcoList1* pITensors, gguf_file_t* pFile, char_t* error, size_t error_size) {
    uint64_t index = 0;
    uint64_t max_end = 0;

    if (pITensors == 0 || pFile == 0) {
        return ECO_E_GGUF1_INVALID_ARGUMENT;
    }

    for (index = 0; index < pFile->header.tensor_count; ++index) {
        IEcoGGUF1TensorInfo* pITensor = (IEcoGGUF1TensorInfo*)pITensors->pVTbl->Item(pITensors, (uint32_t)index);
        ECO_GGUF1_TENSOR_INFO_DESCRIPTOR* pTensorDescriptor = 0;
        IEcoRawData1* pIRawData = 0;
        uint64_t raw_size = 0;
        uint64_t end = 0;

        if (pITensor == 0) {
            CEcoGGUF1_set_error(error, error_size, "Null tensor info at index %" PRIu64, index);
            return ECO_E_GGUF1_FAIL;
        }

        pTensorDescriptor = pITensor->pVTbl->get_Descriptor(pITensor);
        if (pTensorDescriptor == 0) {
            CEcoGGUF1_set_error(error, error_size, "Tensor descriptor is missing");
            return ECO_E_GGUF1_FAIL;
        }

        if (CEcoGGUF1_queryRawData(pITensor->pVTbl->get_RawData(pITensor), &pIRawData) != ECO_E_GGUF1_OK || pIRawData == 0) {
            CEcoGGUF1_set_error(error, error_size, "Tensor '%s' has no raw data", pTensorDescriptor->name);
            return ECO_E_GGUF1_FAIL;
        }

        raw_size = pIRawData->pVTbl->get_Size(pIRawData);
        pIRawData->pVTbl->Release(pIRawData);

        if (pTensorDescriptor->offset > UINT64_MAX - raw_size) {
            CEcoGGUF1_set_error(error, error_size, "Tensor '%s' offset overflow", pTensorDescriptor->name);
            return ECO_E_GGUF1_FAIL;
        }

        end = pTensorDescriptor->offset + raw_size;
        if (end > max_end) {
            max_end = end;
        }
    }

    if (max_end != 0) {
        pFile->tensor_data = (uint8_t*)calloc((size_t)max_end, 1);
        if (pFile->tensor_data == 0) {
            CEcoGGUF1_set_error(error, error_size, "Out of memory allocating tensor data");
            return ECO_E_GGUF1_OUT_OF_MEMORY;
        }
    }
    pFile->tensor_data_size = max_end;

    for (index = 0; index < pFile->header.tensor_count; ++index) {
        IEcoGGUF1TensorInfo* pITensor = (IEcoGGUF1TensorInfo*)pITensors->pVTbl->Item(pITensors, (uint32_t)index);
        ECO_GGUF1_TENSOR_INFO_DESCRIPTOR* pTensorDescriptor = pITensor->pVTbl->get_Descriptor(pITensor);
        IEcoRawData1* pIRawData = 0;
        byte_t* pPointer = 0;
        uint64_t raw_size = 0;

        if (CEcoGGUF1_queryRawData(pITensor->pVTbl->get_RawData(pITensor), &pIRawData) != ECO_E_GGUF1_OK || pIRawData == 0) {
            CEcoGGUF1_set_error(error, error_size, "Tensor '%s' has no raw data", pTensorDescriptor->name);
            return ECO_E_GGUF1_FAIL;
        }

        raw_size = pIRawData->pVTbl->get_Size(pIRawData);
        pPointer = raw_size == 0 ? 0 : pIRawData->pVTbl->get_Pointer(pIRawData, 0);
        if (raw_size != 0 && pPointer == 0) {
            pIRawData->pVTbl->Release(pIRawData);
            CEcoGGUF1_set_error(error, error_size, "Tensor '%s' raw data pointer is invalid", pTensorDescriptor->name);
            return ECO_E_GGUF1_FAIL;
        }

        if (raw_size != 0) {
            memcpy(pFile->tensor_data + pTensorDescriptor->offset, pPointer, (size_t)raw_size);
        }
        pIRawData->pVTbl->Release(pIRawData);
    }

    return ECO_E_GGUF1_OK;
}

static int16_t CEcoGGUF1_convertEcoFileToGGUF(IEcoGGUF1File* pIFile, gguf_file_t* pFile, char_t* error, size_t error_size) {
    ECO_GGUF1_HEADER_DESCRIPTOR* pHeader = 0;
    IEcoList1* pIMetadata = 0;
    IEcoList1* pITensors = 0;
    IEcoUnknown* pIUnknown = 0;
    char_t* pTensorDataSourcePath = 0;
    uint64_t index = 0;
    int16_t result = ECO_E_GGUF1_OK;

    if (pIFile == 0 || pFile == 0) {
        return ECO_E_GGUF1_INVALID_ARGUMENT;
    }

    memset(pFile, 0, sizeof(*pFile));

    pHeader = pIFile->pVTbl->get_Descriptor(pIFile);
    if (pHeader == 0) {
        CEcoGGUF1_set_error(error, error_size, "GGUF file descriptor is missing");
        return ECO_E_GGUF1_FAIL;
    }

    pIMetadata = pIFile->pVTbl->get_MetadataKVs(pIFile);
    pITensors = pIFile->pVTbl->get_TensorInfos(pIFile);

    pFile->header.magic = pHeader->magic == 0 ? ECO_GGUF1_MAGIC : pHeader->magic;
    pFile->header.version = pHeader->version == 0 ? ECO_GGUF1_VERSION_3 : pHeader->version;
    pFile->header.metadata_kv_count = pIMetadata == 0 ? 0 : pIMetadata->pVTbl->Count(pIMetadata);
    pFile->header.tensor_count = pITensors == 0 ? 0 : pITensors->pVTbl->Count(pITensors);
    pFile->alignment = pIFile->pVTbl->get_Alignment(pIFile);

    if (pFile->header.metadata_kv_count != 0) {
        if (pFile->header.metadata_kv_count > (uint64_t)((size_t)-1) / sizeof(gguf_metadata_kv_t)) {
            CEcoGGUF1_set_error(error, error_size, "Too many metadata entries");
            return ECO_E_GGUF1_OUT_OF_MEMORY;
        }
        pFile->metadata_kv = (gguf_metadata_kv_t*)calloc((size_t)pFile->header.metadata_kv_count, sizeof(gguf_metadata_kv_t));
        if (pFile->metadata_kv == 0) {
            CEcoGGUF1_set_error(error, error_size, "Out of memory allocating metadata entries");
            return ECO_E_GGUF1_OUT_OF_MEMORY;
        }
    }

    for (index = 0; index < pFile->header.metadata_kv_count; ++index) {
        IEcoGGUF1MetadataKV* pIKV = (IEcoGGUF1MetadataKV*)pIMetadata->pVTbl->Item(pIMetadata, (uint32_t)index);
        ECO_GGUF1_METADATA_KV_DESCRIPTOR* pKVDescriptor = 0;
        IEcoGGUF1MetadataValue* pIValue = 0;

        if (pIKV == 0) {
            CEcoGGUF1_set_error(error, error_size, "Null metadata entry at index %" PRIu64, index);
            gguf_free(pFile);
            return ECO_E_GGUF1_FAIL;
        }

        pKVDescriptor = pIKV->pVTbl->get_Descriptor(pIKV);
        pIValue = pIKV->pVTbl->get_Value(pIKV);
        if (pKVDescriptor == 0 || pIValue == 0) {
            CEcoGGUF1_set_error(error, error_size, "Metadata entry is incomplete");
            gguf_free(pFile);
            return ECO_E_GGUF1_FAIL;
        }

        result = CEcoGGUF1_alloc_gguf_string(pKVDescriptor->key, pKVDescriptor->key_length, &pFile->metadata_kv[index].key, error, error_size);
        if (result != ECO_E_GGUF1_OK) {
            gguf_free(pFile);
            return result;
        }

        pFile->metadata_kv[index].value_type = pKVDescriptor->value_type;
        result = CEcoGGUF1_convertEcoValueToGGUF(pIValue, &pFile->metadata_kv[index].value, error, error_size);
        if (result != ECO_E_GGUF1_OK) {
            gguf_free(pFile);
            return result;
        }
    }

    if (pFile->header.tensor_count != 0) {
        if (pFile->header.tensor_count > (uint64_t)((size_t)-1) / sizeof(gguf_tensor_info_t)) {
            CEcoGGUF1_set_error(error, error_size, "Too many tensor infos");
            gguf_free(pFile);
            return ECO_E_GGUF1_OUT_OF_MEMORY;
        }
        pFile->tensor_infos = (gguf_tensor_info_t*)calloc((size_t)pFile->header.tensor_count, sizeof(gguf_tensor_info_t));
        if (pFile->tensor_infos == 0) {
            CEcoGGUF1_set_error(error, error_size, "Out of memory allocating tensor infos");
            gguf_free(pFile);
            return ECO_E_GGUF1_OUT_OF_MEMORY;
        }
    }

    for (index = 0; index < pFile->header.tensor_count; ++index) {
        IEcoGGUF1TensorInfo* pITensor = (IEcoGGUF1TensorInfo*)pITensors->pVTbl->Item(pITensors, (uint32_t)index);
        ECO_GGUF1_TENSOR_INFO_DESCRIPTOR* pTensorDescriptor = 0;

        if (pITensor == 0) {
            CEcoGGUF1_set_error(error, error_size, "Null tensor info at index %" PRIu64, index);
            gguf_free(pFile);
            return ECO_E_GGUF1_FAIL;
        }

        pTensorDescriptor = pITensor->pVTbl->get_Descriptor(pITensor);
        if (pTensorDescriptor == 0) {
            CEcoGGUF1_set_error(error, error_size, "Tensor descriptor is missing");
            gguf_free(pFile);
            return ECO_E_GGUF1_FAIL;
        }

        result = CEcoGGUF1_alloc_gguf_string(pTensorDescriptor->name, pTensorDescriptor->name_length, &pFile->tensor_infos[index].name, error, error_size);
        if (result != ECO_E_GGUF1_OK) {
            gguf_free(pFile);
            return result;
        }

        pFile->tensor_infos[index].n_dimensions = pTensorDescriptor->n_dimensions;
        if (pTensorDescriptor->n_dimensions != 0) {
            pFile->tensor_infos[index].dimensions = (uint64_t*)calloc((size_t)pTensorDescriptor->n_dimensions, sizeof(uint64_t));
            if (pFile->tensor_infos[index].dimensions == 0) {
                CEcoGGUF1_set_error(error, error_size, "Out of memory allocating tensor dimensions");
                gguf_free(pFile);
                return ECO_E_GGUF1_OUT_OF_MEMORY;
            }
            memcpy(pFile->tensor_infos[index].dimensions, pTensorDescriptor->dimensions, (size_t)pTensorDescriptor->n_dimensions * sizeof(uint64_t));
        }
        pFile->tensor_infos[index].type = pTensorDescriptor->type;
        pFile->tensor_infos[index].offset = pTensorDescriptor->offset;
    }

    pIUnknown = pIFile->pVTbl->get_TensorData(pIFile);
    if (pIUnknown != 0) {
        result = CEcoGGUF1_copyRawDataObject(pIUnknown, &pFile->tensor_data, &pFile->tensor_data_size, error, error_size);
        if (result != ECO_E_GGUF1_OK) {
            gguf_free(pFile);
            return result;
        }
    }
    else if ((pTensorDataSourcePath = pIFile->pVTbl->get_TensorDataSourcePath(pIFile)) != 0) {
        result = CEcoGGUF1_alloc_c_string(pTensorDataSourcePath, &pFile->tensor_data_source_path, error, error_size);
        if (result != ECO_E_GGUF1_OK) {
            gguf_free(pFile);
            return result;
        }
        pFile->tensor_data_source_offset = pIFile->pVTbl->get_TensorDataSourceOffset(pIFile);
        pFile->tensor_data_source_size = pIFile->pVTbl->get_TensorDataSourceSize(pIFile);
        pFile->tensor_data_size = pFile->tensor_data_source_size;
    }
    else if (pFile->header.tensor_count != 0) {
        result = CEcoGGUF1_buildTensorDataFromSections(pITensors, pFile, error, error_size);
        if (result != ECO_E_GGUF1_OK) {
            gguf_free(pFile);
            return result;
        }
    }

    return ECO_E_GGUF1_OK;
}

int16_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1_QueryInterface(IEcoGGUF1Ptr_t me, const UGUID* riid, voidptr_t* ppv) {
    if (me == 0 || ppv == 0) {
        return -1;
    }

    if (IsEqualUGUID(riid, &IID_IEcoGGUF1) || IsEqualUGUID(riid, &IID_IEcoUnknown)) {
        *ppv = me;
        me->pVTbl->AddRef(me);
        return 0;
    }

    *ppv = 0;
    return -1;
}

uint32_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1_AddRef(IEcoGGUF1Ptr_t me) {
    CEcoGGUF1_6EAA44B1* pCMe = (CEcoGGUF1_6EAA44B1*)me;

    if (me == 0) {
        return (uint32_t)-1;
    }

    return ++pCMe->m_cRef;
}

void ECOCALLMETHOD deleteCEcoGGUF1_6EAA44B1(IEcoGGUF1Ptr_t pIGGUF1) {
    CEcoGGUF1_6EAA44B1* pCMe = (CEcoGGUF1_6EAA44B1*)pIGGUF1;
    IEcoMemoryAllocator1* pIMem = 0;

    if (pCMe == 0) {
        return;
    }

    pIMem = pCMe->m_pIMem;

    if (pCMe->m_pIFileMgr != 0) {
        pCMe->m_pIFileMgr->pVTbl->Release(pCMe->m_pIFileMgr);
    }

    if (pCMe->m_pIStr != 0) {
        pCMe->m_pIStr->pVTbl->Release(pCMe->m_pIStr);
    }

    if (pCMe->m_pIBus != 0) {
        pCMe->m_pIBus->pVTbl->Release(pCMe->m_pIBus);
    }

    if (pCMe->m_pISys != 0) {
        pCMe->m_pISys->pVTbl->Release(pCMe->m_pISys);
    }

    if (pIMem != 0) {
        pIMem->pVTbl->Free(pIMem, pCMe);
        pIMem->pVTbl->Release(pIMem);
    }
}

uint32_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1_Release(IEcoGGUF1Ptr_t me) {
    CEcoGGUF1_6EAA44B1* pCMe = (CEcoGGUF1_6EAA44B1*)me;

    if (me == 0) {
        return (uint32_t)-1;
    }

    --pCMe->m_cRef;
    if (pCMe->m_cRef == 0) {
        deleteCEcoGGUF1_6EAA44B1((IEcoGGUF1*)pCMe);
        return 0;
    }

    return pCMe->m_cRef;
}

IEcoGGUF1File* ECOCALLMETHOD CEcoGGUF1_6EAA44B1_readFile(IEcoGGUF1Ptr_t me, char_t* fileName) {
    gguf_file_t file;
    IEcoGGUF1File* pIFile = 0;
    char_t error[512] = {0};

    if (me == 0 || fileName == 0) {
        return 0;
    }

    memset(&file, 0, sizeof(file));
    if (gguf_load_file(fileName, &file, error, sizeof(error)) != GGUF_STATUS_OK) {
        return 0;
    }

    if (CEcoGGUF1_convertGGUFToEcoFile(me, &file, &pIFile) != ECO_E_GGUF1_OK) {
        gguf_free(&file);
        return 0;
    }

    gguf_free(&file);
    return pIFile;
}

int16_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1_writeFile(IEcoGGUF1Ptr_t me, IEcoGGUF1File* pIFile, char_t* fileName) {
    gguf_file_t file;
    char_t error[512] = {0};
    int16_t result = ECO_E_GGUF1_OK;

    if (me == 0 || pIFile == 0 || fileName == 0) {
        return ECO_E_GGUF1_INVALID_ARGUMENT;
    }

    memset(&file, 0, sizeof(file));
    result = CEcoGGUF1_convertEcoFileToGGUF(pIFile, &file, error, sizeof(error));
    if (result != ECO_E_GGUF1_OK) {
        return result;
    }

    result = CEcoGGUF1_map_status(gguf_save_file(fileName, &file, error, sizeof(error)));
    gguf_free(&file);
    return result;
}

IEcoGGUF1File* ECOCALLMETHOD CEcoGGUF1_6EAA44B1_readFileFromMemory(IEcoGGUF1Ptr_t me, byte_t* ptr, uint64_t size) {
    gguf_file_t file;
    IEcoGGUF1File* pIFile = 0;
    char_t error[512] = {0};

    if (me == 0 || ptr == 0 || size == 0) {
        return 0;
    }

    memset(&file, 0, sizeof(file));
    if (gguf_load_memory(ptr, size, &file, error, sizeof(error)) != GGUF_STATUS_OK) {
        return 0;
    }

    if (CEcoGGUF1_convertGGUFToEcoFile(me, &file, &pIFile) != ECO_E_GGUF1_OK) {
        gguf_free(&file);
        return 0;
    }

    gguf_free(&file);
    return pIFile;
}

int16_t ECOCALLMETHOD CEcoGGUF1_6EAA44B1_writeFileToMemory(IEcoGGUF1Ptr_t me, IEcoGGUF1File* pIFile, byte_t** ptr, uint64_t* size) {
    CEcoGGUF1_6EAA44B1* pCMe = (CEcoGGUF1_6EAA44B1*)me;
    gguf_file_t file;
    uint8_t* serialized = 0;
    uint64_t serialized_size = 0;
    char_t error[512] = {0};
    int16_t result = ECO_E_GGUF1_OK;

    if (me == 0 || pIFile == 0 || ptr == 0 || size == 0 || pCMe->m_pIMem == 0) {
        return ECO_E_GGUF1_INVALID_ARGUMENT;
    }

    *ptr = 0;
    *size = 0;
    memset(&file, 0, sizeof(file));

    result = CEcoGGUF1_convertEcoFileToGGUF(pIFile, &file, error, sizeof(error));
    if (result != ECO_E_GGUF1_OK) {
        return result;
    }

    result = CEcoGGUF1_map_status(gguf_serialized_size(&file, &serialized_size, error, sizeof(error)));
    if (result != ECO_E_GGUF1_OK) {
        gguf_free(&file);
        return result;
    }

    if (serialized_size > UINT32_MAX) {
        gguf_free(&file);
        return ECO_E_GGUF1_OUT_OF_MEMORY;
    }

    serialized_size = 0;
    result = CEcoGGUF1_map_status(gguf_serialize_to_memory(&file, &serialized, &serialized_size, error, sizeof(error)));
    if (result != ECO_E_GGUF1_OK) {
        gguf_free(&file);
        return result;
    }

    if (serialized_size > UINT32_MAX) {
        free(serialized);
        gguf_free(&file);
        return ECO_E_GGUF1_OUT_OF_MEMORY;
    }

    *ptr = (byte_t*)pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, (uint32_t)serialized_size);
    if (serialized_size != 0 && *ptr == 0) {
        free(serialized);
        gguf_free(&file);
        return ECO_E_GGUF1_OUT_OF_MEMORY;
    }

    if (serialized_size != 0) {
        memcpy(*ptr, serialized, (size_t)serialized_size);
    }
    *size = serialized_size;

    free(serialized);
    gguf_free(&file);
    return ECO_E_GGUF1_OK;
}

IEcoGGUF1File* ECOCALLMETHOD CEcoGGUF1_6EAA44B1_createFile(IEcoGGUF1Ptr_t me) {
    CEcoGGUF1_6EAA44B1* pCMe = (CEcoGGUF1_6EAA44B1*)me;
    IEcoGGUF1File* pIFile = 0;

    if (me == 0) {
        return 0;
    }

    createCEcoGGUF1_6EAA44B1File((IEcoUnknown*)pCMe->m_pISys, 0, &pIFile);
    return pIFile;
}

IEcoGGUF1TensorInfo* ECOCALLMETHOD CEcoGGUF1_6EAA44B1_createTensorInfo(IEcoGGUF1Ptr_t me) {
    CEcoGGUF1_6EAA44B1* pCMe = (CEcoGGUF1_6EAA44B1*)me;
    IEcoGGUF1TensorInfo* pIInfo = 0;

    if (me == 0) {
        return 0;
    }

    createCEcoGGUF1_6EAA44B1TensorInfo((IEcoUnknown*)pCMe->m_pISys, 0, &pIInfo);
    return pIInfo;
}

IEcoGGUF1MetadataKV* ECOCALLMETHOD CEcoGGUF1_6EAA44B1_createMetadataKV(IEcoGGUF1Ptr_t me) {
    CEcoGGUF1_6EAA44B1* pCMe = (CEcoGGUF1_6EAA44B1*)me;
    IEcoGGUF1MetadataKV* pIKV = 0;

    if (me == 0) {
        return 0;
    }

    createCEcoGGUF1_6EAA44B1MetadataKV((IEcoUnknown*)pCMe->m_pISys, 0, &pIKV);
    return pIKV;
}

IEcoGGUF1MetadataValue* ECOCALLMETHOD CEcoGGUF1_6EAA44B1_createMetadataValue(IEcoGGUF1Ptr_t me) {
    CEcoGGUF1_6EAA44B1* pCMe = (CEcoGGUF1_6EAA44B1*)me;
    IEcoGGUF1MetadataValue* pIValue = 0;

    if (me == 0) {
        return 0;
    }

    createCEcoGGUF1_6EAA44B1MetadataValue((IEcoUnknown*)pCMe->m_pISys, 0, &pIValue);
    return pIValue;
}

IEcoRawData1* ECOCALLMETHOD CEcoGGUF1_6EAA44B1_createRawData(IEcoGGUF1Ptr_t me) {
    CEcoGGUF1_6EAA44B1* pCMe = (CEcoGGUF1_6EAA44B1*)me;
    IEcoRawData1* pIRawData = 0;

    if (me == 0) {
        return 0;
    }

    createCEcoGGUF1_6EAA44B1RawData((IEcoUnknown*)pCMe->m_pISys, 0, &pIRawData);
    return pIRawData;
}

static IEcoGGUF1VTbl g_xEcoGGUF1VTbl = {
    CEcoGGUF1_6EAA44B1_QueryInterface,
    CEcoGGUF1_6EAA44B1_AddRef,
    CEcoGGUF1_6EAA44B1_Release,
    CEcoGGUF1_6EAA44B1_readFile,
    CEcoGGUF1_6EAA44B1_writeFile,
    CEcoGGUF1_6EAA44B1_readFileFromMemory,
    CEcoGGUF1_6EAA44B1_writeFileToMemory,
    CEcoGGUF1_6EAA44B1_createFile,
    CEcoGGUF1_6EAA44B1_createTensorInfo,
    CEcoGGUF1_6EAA44B1_createMetadataKV,
    CEcoGGUF1_6EAA44B1_createMetadataValue,
    CEcoGGUF1_6EAA44B1_createRawData
};

int16_t ECOCALLMETHOD initCEcoGGUF1_6EAA44B1(IEcoGGUF1Ptr_t me, IEcoUnknownPtr_t pIUnkSystem) {
    CEcoGGUF1_6EAA44B1* pCMe = (CEcoGGUF1_6EAA44B1*)me;
    int16_t result = -1;

    (void)pIUnkSystem;

    if (me == 0 || pCMe->m_pIBus == 0) {
        return -1;
    }

    if (pCMe->m_pIStr == 0) {
        result = pCMe->m_pIBus->pVTbl->QueryComponent(pCMe->m_pIBus, &CID_EcoString1, 0, &IID_IEcoString1, (void**)&pCMe->m_pIStr);
        if (result != 0) {
            return result;
        }
    }

    if (pCMe->m_pIFileMgr == 0) {
        result = pCMe->m_pIBus->pVTbl->QueryComponent(pCMe->m_pIBus, &CID_EcoFileSystemManagement1, 0, &IID_IEcoFileManager1, (void**)&pCMe->m_pIFileMgr);
        if (result != 0) {
            return result;
        }
    }

    return 0;
}

int16_t ECOCALLMETHOD createCEcoGGUF1_6EAA44B1(IEcoUnknownPtr_t pIUnkSystem, IEcoUnknownPtr_t pIUnkOuter, IEcoGGUF1Ptr_t* ppIGGUF1) {
    IEcoSystem1* pISys = 0;
    IEcoInterfaceBus1* pIBus = 0;
    IEcoMemoryAllocator1* pIMem = 0;
    CEcoGGUF1_6EAA44B1* pCMe = 0;
    int16_t result = -1;

    (void)pIUnkOuter;

    if (ppIGGUF1 == 0 || pIUnkSystem == 0) {
        return -1;
    }

    *ppIGGUF1 = 0;

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
    if (result != 0 || pIMem == 0) {
        pIBus->pVTbl->Release(pIBus);
        pISys->pVTbl->Release(pISys);
        return -1;
    }

    pCMe = (CEcoGGUF1_6EAA44B1*)pIMem->pVTbl->Alloc(pIMem, sizeof(CEcoGGUF1_6EAA44B1));
    if (pCMe == 0) {
        pIMem->pVTbl->Release(pIMem);
        pIBus->pVTbl->Release(pIBus);
        pISys->pVTbl->Release(pISys);
        return -1;
    }

    pCMe->m_pVTblIGGUF1 = &g_xEcoGGUF1VTbl;
    pCMe->m_cRef = 1;
    pCMe->m_pIMem = pIMem;
    pCMe->m_pISys = pISys;
    pCMe->m_pIBus = pIBus;
    pCMe->m_pIStr = 0;
    pCMe->m_pIFileMgr = 0;

    *ppIGGUF1 = (IEcoGGUF1*)pCMe;
    return 0;
}
