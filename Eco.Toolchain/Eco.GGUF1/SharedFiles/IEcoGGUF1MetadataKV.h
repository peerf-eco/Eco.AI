#ifndef __I_ECO_GGUF_1_METADATA_KV_H__
#define __I_ECO_GGUF_1_METADATA_KV_H__

#include "IEcoBase1.h"
#include "IEcoGGUF1MetadataValue.h"

typedef struct ECO_GGUF1_METADATA_KV_DESCRIPTOR {
    uint64_t key_length;
    char_t* key;
    uint32_t value_type;
} ECO_GGUF1_METADATA_KV_DESCRIPTOR;

/* IEcoGGUF1MetadataKV IID = {5B446E12-2901-4F90-B390-26A35EAA3A1D} */
#ifndef __IID_IEcoGGUF1MetadataKV
static const UGUID IID_IEcoGGUF1MetadataKV = {0x01, 0x10, {0x5B, 0x44, 0x6E, 0x12, 0x29, 0x01, 0x4F, 0x90, 0xB3, 0x90, 0x26, 0xA3, 0x5E, 0xAA, 0x3A, 0x1D}};
#endif

typedef struct IEcoGGUF1MetadataKV* IEcoGGUF1MetadataKVPtr_t;

typedef struct IEcoGGUF1MetadataKVVTbl {
    int16_t (ECOCALLMETHOD *QueryInterface)(IEcoGGUF1MetadataKVPtr_t me, const UGUID* riid, voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(IEcoGGUF1MetadataKVPtr_t me);
    uint32_t (ECOCALLMETHOD *Release)(IEcoGGUF1MetadataKVPtr_t me);

    ECO_GGUF1_METADATA_KV_DESCRIPTOR* (ECOCALLMETHOD *get_Descriptor)(IEcoGGUF1MetadataKVPtr_t me);
    void (ECOCALLMETHOD *set_Descriptor)(IEcoGGUF1MetadataKVPtr_t me, ECO_GGUF1_METADATA_KV_DESCRIPTOR* descriptor);
    char_t* (ECOCALLMETHOD *get_Key)(IEcoGGUF1MetadataKVPtr_t me);
    void (ECOCALLMETHOD *set_Key)(IEcoGGUF1MetadataKVPtr_t me, char_t* key);
    IEcoGGUF1MetadataValue* (ECOCALLMETHOD *get_Value)(IEcoGGUF1MetadataKVPtr_t me);
    void (ECOCALLMETHOD *set_Value)(IEcoGGUF1MetadataKVPtr_t me, IEcoGGUF1MetadataValue* pIValue);
    void (ECOCALLMETHOD *set_KeyBytes)(IEcoGGUF1MetadataKVPtr_t me, char_t* key, uint64_t len);
} IEcoGGUF1MetadataKVVTbl, *IEcoGGUF1MetadataKVVTblPtr;

interface IEcoGGUF1MetadataKV {
    struct IEcoGGUF1MetadataKVVTbl* pVTbl;
} IEcoGGUF1MetadataKV;

#endif /* __I_ECO_GGUF_1_METADATA_KV_H__ */
