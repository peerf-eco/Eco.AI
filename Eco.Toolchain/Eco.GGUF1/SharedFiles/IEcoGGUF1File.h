#ifndef __I_ECO_GGUF_1_FILE_H__
#define __I_ECO_GGUF_1_FILE_H__

#include "IEcoBase1.h"
#include "IEcoList1.h"
#include "DefEcoGGUF1.h"
#include "IEcoGGUF1MetadataKV.h"
#include "IEcoGGUF1TensorInfo.h"

typedef struct ECO_GGUF1_HEADER_DESCRIPTOR {
    uint32_t magic;
    uint32_t version;
    uint64_t tensor_count;
    uint64_t metadata_kv_count;
    uint64_t tensor_data_offset;
} ECO_GGUF1_HEADER_DESCRIPTOR;

/* IEcoGGUF1File IID = {B2D9CBE3-8ACD-4F88-B0AA-B05D3C748A3A} */
#ifndef __IID_IEcoGGUF1File
static const UGUID IID_IEcoGGUF1File = {0x01, 0x10, {0xB2, 0xD9, 0xCB, 0xE3, 0x8A, 0xCD, 0x4F, 0x88, 0xB0, 0xAA, 0xB0, 0x5D, 0x3C, 0x74, 0x8A, 0x3A}};
#endif

typedef struct IEcoGGUF1File* IEcoGGUF1FilePtr_t;

typedef struct IEcoGGUF1FileVTbl {
    int16_t (ECOCALLMETHOD *QueryInterface)(IEcoGGUF1FilePtr_t me, const UGUID* riid, voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(IEcoGGUF1FilePtr_t me);
    uint32_t (ECOCALLMETHOD *Release)(IEcoGGUF1FilePtr_t me);

    ECO_GGUF1_HEADER_DESCRIPTOR* (ECOCALLMETHOD *get_Descriptor)(IEcoGGUF1FilePtr_t me);
    void (ECOCALLMETHOD *set_Descriptor)(IEcoGGUF1FilePtr_t me, ECO_GGUF1_HEADER_DESCRIPTOR* descriptor);
    uint32_t (ECOCALLMETHOD *get_Alignment)(IEcoGGUF1FilePtr_t me);
    void (ECOCALLMETHOD *set_Alignment)(IEcoGGUF1FilePtr_t me, uint32_t alignment);
    IEcoList1* (ECOCALLMETHOD *get_MetadataKVs)(IEcoGGUF1FilePtr_t me);
    void (ECOCALLMETHOD *set_MetadataKVs)(IEcoGGUF1FilePtr_t me, IEcoList1* pIEntries);
    IEcoList1* (ECOCALLMETHOD *get_TensorInfos)(IEcoGGUF1FilePtr_t me);
    void (ECOCALLMETHOD *set_TensorInfos)(IEcoGGUF1FilePtr_t me, IEcoList1* pIInfos);
    IEcoUnknown* (ECOCALLMETHOD *get_TensorData)(IEcoGGUF1FilePtr_t me);
    void (ECOCALLMETHOD *set_TensorData)(IEcoGGUF1FilePtr_t me, IEcoUnknown* pIRawData);
    char_t* (ECOCALLMETHOD *get_TensorDataSourcePath)(IEcoGGUF1FilePtr_t me);
    uint64_t (ECOCALLMETHOD *get_TensorDataSourceOffset)(IEcoGGUF1FilePtr_t me);
    uint64_t (ECOCALLMETHOD *get_TensorDataSourceSize)(IEcoGGUF1FilePtr_t me);
    void (ECOCALLMETHOD *set_TensorDataSource)(IEcoGGUF1FilePtr_t me, char_t* path, uint64_t offset, uint64_t size);
} IEcoGGUF1FileVTbl, *IEcoGGUF1FileVTblPtr;

interface IEcoGGUF1File {
    struct IEcoGGUF1FileVTbl* pVTbl;
} IEcoGGUF1File;

#endif /* __I_ECO_GGUF_1_FILE_H__ */
