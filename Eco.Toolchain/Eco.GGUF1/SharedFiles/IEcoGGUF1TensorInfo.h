#ifndef __I_ECO_GGUF_1_TENSOR_INFO_H__
#define __I_ECO_GGUF_1_TENSOR_INFO_H__

#include "IEcoBase1.h"
#include "DefEcoGGUF1.h"

typedef struct ECO_GGUF1_TENSOR_INFO_DESCRIPTOR {
    uint64_t name_length;
    char_t name[ECO_GGUF1_MAX_TENSOR_NAME + 1];
    uint32_t n_dimensions;
    uint64_t dimensions[ECO_GGUF1_MAX_DIMS];
    uint32_t type;
    uint64_t offset;
} ECO_GGUF1_TENSOR_INFO_DESCRIPTOR;

/* IEcoGGUF1TensorInfo IID = {64D1D0C8-CBC2-4D92-B646-C6C312C46E0C} */
#ifndef __IID_IEcoGGUF1TensorInfo
static const UGUID IID_IEcoGGUF1TensorInfo = {0x01, 0x10, {0x64, 0xD1, 0xD0, 0xC8, 0xCB, 0xC2, 0x4D, 0x92, 0xB6, 0x46, 0xC6, 0xC3, 0x12, 0xC4, 0x6E, 0x0C}};
#endif

typedef struct IEcoGGUF1TensorInfo* IEcoGGUF1TensorInfoPtr_t;

typedef struct IEcoGGUF1TensorInfoVTbl {
    int16_t (ECOCALLMETHOD *QueryInterface)(IEcoGGUF1TensorInfoPtr_t me, const UGUID* riid, voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(IEcoGGUF1TensorInfoPtr_t me);
    uint32_t (ECOCALLMETHOD *Release)(IEcoGGUF1TensorInfoPtr_t me);

    ECO_GGUF1_TENSOR_INFO_DESCRIPTOR* (ECOCALLMETHOD *get_Descriptor)(IEcoGGUF1TensorInfoPtr_t me);
    void (ECOCALLMETHOD *set_Descriptor)(IEcoGGUF1TensorInfoPtr_t me, ECO_GGUF1_TENSOR_INFO_DESCRIPTOR* descriptor);
    char_t* (ECOCALLMETHOD *get_Name)(IEcoGGUF1TensorInfoPtr_t me);
    void (ECOCALLMETHOD *set_Name)(IEcoGGUF1TensorInfoPtr_t me, char_t* name);
    IEcoUnknown* (ECOCALLMETHOD *get_RawData)(IEcoGGUF1TensorInfoPtr_t me);
    void (ECOCALLMETHOD *set_RawData)(IEcoGGUF1TensorInfoPtr_t me, IEcoUnknown* pIRawData);
} IEcoGGUF1TensorInfoVTbl, *IEcoGGUF1TensorInfoVTblPtr;

interface IEcoGGUF1TensorInfo {
    struct IEcoGGUF1TensorInfoVTbl* pVTbl;
} IEcoGGUF1TensorInfo;

#endif /* __I_ECO_GGUF_1_TENSOR_INFO_H__ */
