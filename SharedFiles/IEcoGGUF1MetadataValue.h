#ifndef __I_ECO_GGUF_1_METADATA_VALUE_H__
#define __I_ECO_GGUF_1_METADATA_VALUE_H__

#include "IEcoBase1.h"
#include "IEcoList1.h"
#include "DefEcoGGUF1.h"

typedef struct ECO_GGUF1_STRING_DESCRIPTOR {
    uint64_t len;
    char_t* string;
} ECO_GGUF1_STRING_DESCRIPTOR;

typedef struct ECO_GGUF1_METADATA_ARRAY_DESCRIPTOR {
    uint32_t type;
    uint64_t len;
} ECO_GGUF1_METADATA_ARRAY_DESCRIPTOR;

typedef struct ECO_GGUF1_METADATA_VALUE_DESCRIPTOR {
    uint32_t value_type;
    uint8_t uint8_value;
    int8_t int8_value;
    uint16_t uint16_value;
    int16_t int16_value;
    uint32_t uint32_value;
    int32_t int32_value;
    float float32_value;
    uint64_t uint64_value;
    int64_t int64_value;
    double float64_value;
    bool_t bool_value;
    ECO_GGUF1_STRING_DESCRIPTOR string;
    ECO_GGUF1_METADATA_ARRAY_DESCRIPTOR array;
} ECO_GGUF1_METADATA_VALUE_DESCRIPTOR;

/* IEcoGGUF1MetadataValue IID = {9A79E8A2-312A-4D96-A4CB-ED16F767B7D1} */
#ifndef __IID_IEcoGGUF1MetadataValue
static const UGUID IID_IEcoGGUF1MetadataValue = {0x01, 0x10, {0x9A, 0x79, 0xE8, 0xA2, 0x31, 0x2A, 0x4D, 0x96, 0xA4, 0xCB, 0xED, 0x16, 0xF7, 0x67, 0xB7, 0xD1}};
#endif

typedef struct IEcoGGUF1MetadataValue* IEcoGGUF1MetadataValuePtr_t;

typedef struct IEcoGGUF1MetadataValueVTbl {
    int16_t (ECOCALLMETHOD *QueryInterface)(IEcoGGUF1MetadataValuePtr_t me, const UGUID* riid, voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(IEcoGGUF1MetadataValuePtr_t me);
    uint32_t (ECOCALLMETHOD *Release)(IEcoGGUF1MetadataValuePtr_t me);

    ECO_GGUF1_METADATA_VALUE_DESCRIPTOR* (ECOCALLMETHOD *get_Descriptor)(IEcoGGUF1MetadataValuePtr_t me);
    void (ECOCALLMETHOD *set_Descriptor)(IEcoGGUF1MetadataValuePtr_t me, ECO_GGUF1_METADATA_VALUE_DESCRIPTOR* descriptor);
    IEcoList1* (ECOCALLMETHOD *get_ArrayItems)(IEcoGGUF1MetadataValuePtr_t me);
    void (ECOCALLMETHOD *set_ArrayItems)(IEcoGGUF1MetadataValuePtr_t me, IEcoList1* pIItems);
    char_t* (ECOCALLMETHOD *get_String)(IEcoGGUF1MetadataValuePtr_t me);
    void (ECOCALLMETHOD *set_String)(IEcoGGUF1MetadataValuePtr_t me, char_t* value);
    void (ECOCALLMETHOD *set_StringBytes)(IEcoGGUF1MetadataValuePtr_t me, char_t* value, uint64_t len);
} IEcoGGUF1MetadataValueVTbl, *IEcoGGUF1MetadataValueVTblPtr;

interface IEcoGGUF1MetadataValue {
    struct IEcoGGUF1MetadataValueVTbl* pVTbl;
} IEcoGGUF1MetadataValue;

#endif /* __I_ECO_GGUF_1_METADATA_VALUE_H__ */
