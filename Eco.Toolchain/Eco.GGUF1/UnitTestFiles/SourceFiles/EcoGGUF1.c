#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"
#include "IdEcoInterfaceBus1.h"
#include "IdEcoString1.h"
#include "IdEcoList1.h"
#include "IdEcoLog1.h"
#include "IEcoLog1FileAffiliate.h"
#include "IdEcoGGUF1.h"

#include <stdio.h>

static void testCreateInMemoryGGUF(IEcoInterfaceBus1* pIBus, IEcoLog1* pILog, IEcoGGUF1* pIGGUF) {
    IEcoGGUF1File* pIFile = 0;
    IEcoGGUF1MetadataKV* pIKV = 0;
    IEcoGGUF1MetadataValue* pIValue = 0;
    IEcoGGUF1TensorInfo* pITensor = 0;
    IEcoList1* pIMetadata = 0;
    IEcoList1* pITensors = 0;
    ECO_GGUF1_METADATA_VALUE_DESCRIPTOR* pValueDescriptor = 0;
    ECO_GGUF1_TENSOR_INFO_DESCRIPTOR* pTensorDescriptor = 0;

    if (pIBus == 0 || pILog == 0 || pIGGUF == 0) {
        return;
    }

    pILog->pVTbl->Info(pILog, "*** Test Create In-Memory GGUF ***");

    pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoList1, 0, &IID_IEcoList1, (void**)&pIMetadata);
    pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoList1, 0, &IID_IEcoList1, (void**)&pITensors);
    if (pIMetadata == 0 || pITensors == 0) {
        pILog->pVTbl->Error(pILog, "Unable to create Eco.List1 instances");
        goto Release;
    }

    pIFile = pIGGUF->pVTbl->createFile(pIGGUF);
    pIKV = pIGGUF->pVTbl->createMetadataKV(pIGGUF);
    pIValue = pIGGUF->pVTbl->createMetadataValue(pIGGUF);
    pITensor = pIGGUF->pVTbl->createTensorInfo(pIGGUF);
    if (pIFile == 0 || pIKV == 0 || pIValue == 0 || pITensor == 0) {
        pILog->pVTbl->Error(pILog, "Unable to allocate GGUF model objects");
        goto Release;
    }

    pValueDescriptor = pIValue->pVTbl->get_Descriptor(pIValue);
    pValueDescriptor->value_type = ECO_GGUF1_METADATA_VALUE_TYPE_STRING;
    pIValue->pVTbl->set_String(pIValue, "llama");
    pIKV->pVTbl->set_Key(pIKV, ECO_GGUF1_KEY_GENERAL_ARCHITECTURE);
    pIKV->pVTbl->set_Value(pIKV, pIValue);
    pIMetadata->pVTbl->Add(pIMetadata, pIKV);

    pTensorDescriptor = pITensor->pVTbl->get_Descriptor(pITensor);
    pITensor->pVTbl->set_Name(pITensor, "token_embd.weight");
    pTensorDescriptor->n_dimensions = 2;
    pTensorDescriptor->dimensions[0] = 32000;
    pTensorDescriptor->dimensions[1] = 4096;
    pTensorDescriptor->type = ECO_GGUF1_TENSOR_TYPE_F16;
    pTensorDescriptor->offset = 0;
    pITensors->pVTbl->Add(pITensors, pITensor);

    pIFile->pVTbl->set_MetadataKVs(pIFile, pIMetadata);
    pIFile->pVTbl->set_TensorInfos(pIFile, pITensors);

    pILog->pVTbl->InfoFormat(pILog, "Alignment = %u", pIFile->pVTbl->get_Alignment(pIFile));
    pILog->pVTbl->InfoFormat(pILog, "Metadata Entries = %u", (uint32_t)pIFile->pVTbl->get_Descriptor(pIFile)->metadata_kv_count);
    pILog->pVTbl->InfoFormat(pILog, "Tensor Infos = %u", (uint32_t)pIFile->pVTbl->get_Descriptor(pIFile)->tensor_count);

Release:
    if (pITensors != 0) {
        pITensors->pVTbl->Release(pITensors);
    }
    if (pIMetadata != 0) {
        pIMetadata->pVTbl->Release(pIMetadata);
    }
    if (pITensor != 0) {
        pITensor->pVTbl->Release(pITensor);
    }
    if (pIValue != 0) {
        pIValue->pVTbl->Release(pIValue);
    }
    if (pIKV != 0) {
        pIKV->pVTbl->Release(pIKV);
    }
    if (pIFile != 0) {
        pIFile->pVTbl->Release(pIFile);
    }
}

static void logGGUFHeader(IEcoLog1* pILog, char_t* label, IEcoGGUF1File* pIFile) {
    ECO_GGUF1_HEADER_DESCRIPTOR* pDescriptor = 0;

    if (pILog == 0 || pIFile == 0) {
        return;
    }

    pDescriptor = pIFile->pVTbl->get_Descriptor(pIFile);
    if (pDescriptor == 0) {
        return;
    }

    pILog->pVTbl->InfoFormat(pILog, "%s format=GGUF magic=0x%08X version=%u metadata=%llu tensors=%llu tensor_data_offset=%llu",
                             label,
                             pDescriptor->magic,
                             pDescriptor->version,
                             (unsigned long long)pDescriptor->metadata_kv_count,
                             (unsigned long long)pDescriptor->tensor_count,
                             (unsigned long long)pDescriptor->tensor_data_offset);
}

static void testLoadAndResaveGGUF(IEcoLog1* pILog, IEcoGGUF1* pIGGUF) {
    IEcoGGUF1File* pISourceFile = 0;
    IEcoGGUF1File* pIResavedFile = 0;
    FILE* pFile = 0;
    int16_t result = 0;
    char_t* pszInputFile = "C:\\Peerf\\ECO_GGUF\\UnitTestFiles\\TestFiles\\tinygemma3-Q8_0.gguf";
    char_t* pszOutputFile = "C:\\Peerf\\ECO_GGUF\\UnitTestFiles\\TestFiles\\tinygemma3-Q8_0.eco.resaved.gguf";

    if (pILog == 0 || pIGGUF == 0) {
        return;
    }

    pFile = fopen(pszInputFile, "rb");
    if (pFile == 0) {
        pILog->pVTbl->Info(pILog, "*** GGUF round-trip test skipped: input file not found ***");
        return;
    }
    fclose(pFile);

    pILog->pVTbl->Info(pILog, "*** Test Load And Resave GGUF ***");

    pISourceFile = pIGGUF->pVTbl->readFile(pIGGUF, pszInputFile);
    if (pISourceFile == 0) {
        pILog->pVTbl->Error(pILog, "Unable to load GGUF test file");
        goto Release;
    }

    logGGUFHeader(pILog, "source", pISourceFile);

    result = pIGGUF->pVTbl->writeFile(pIGGUF, pISourceFile, pszOutputFile);
    if (result != 0) {
        pILog->pVTbl->ErrorFormat(pILog, "Unable to save GGUF test file, result = %d", result);
        goto Release;
    }

    pIResavedFile = pIGGUF->pVTbl->readFile(pIGGUF, pszOutputFile);
    if (pIResavedFile == 0) {
        pILog->pVTbl->Error(pILog, "Unable to reload resaved GGUF test file");
        goto Release;
    }

    logGGUFHeader(pILog, "resaved", pIResavedFile);

Release:
    if (pIResavedFile != 0) {
        pIResavedFile->pVTbl->Release(pIResavedFile);
    }
    if (pISourceFile != 0) {
        pISourceFile->pVTbl->Release(pISourceFile);
    }
}

int16_t EcoMain(IEcoUnknown* pIUnk) {
    int16_t result = -1;
    IEcoSystem1* pISys = 0;
    IEcoInterfaceBus1* pIBus = 0;
    IEcoLog1* pILog = 0;
    IEcoLog1FileAffiliate* pIFileAffiliate = 0;
    IEcoGGUF1* pIGGUF = 0;

    result = pIUnk->pVTbl->QueryInterface(pIUnk, &GID_IEcoSystem, (void**)&pISys);
    if (result != 0 || pISys == 0) {
        goto Release;
    }

    result = pISys->pVTbl->QueryInterface(pISys, &IID_IEcoInterfaceBus1, (void**)&pIBus);
    if (result != 0 || pIBus == 0) {
        goto Release;
    }

#ifdef ECO_LIB
    pIBus->pVTbl->RegisterComponent(pIBus, &CID_EcoGGUF1, (IEcoUnknown*)GetIEcoComponentFactoryPtr_A1C53A779BCB4AD78B634F1A6EAA44B1);
#endif

    pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoLog1, 0, &IID_IEcoLog1, (void**)&pILog);
    if (pILog != 0) {
        pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoLog1, 0, &IID_IEcoLog1FileAffiliate, (void**)&pIFileAffiliate);
        if (pIFileAffiliate != 0) {
            pILog->pVTbl->AddAffiliate(pILog, (IEcoLog1Affiliate*)pIFileAffiliate);
            pIFileAffiliate->pVTbl->Release(pIFileAffiliate);
        }
    }

    result = pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoGGUF1, 0, &IID_IEcoGGUF1, (void**)&pIGGUF);
    if (result != 0 || pIGGUF == 0) {
        goto Release;
    }

    testCreateInMemoryGGUF(pIBus, pILog, pIGGUF);
    testLoadAndResaveGGUF(pILog, pIGGUF);

Release:
    if (pIGGUF != 0) {
        pIGGUF->pVTbl->Release(pIGGUF);
    }
    if (pILog != 0) {
        pILog->pVTbl->Release(pILog);
    }
    if (pIBus != 0) {
        pIBus->pVTbl->Release(pIBus);
    }
    if (pISys != 0) {
        pISys->pVTbl->Release(pISys);
    }

    return result;
}
