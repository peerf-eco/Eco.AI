#ifndef __I_ECO_GGUF_1_H__
#define __I_ECO_GGUF_1_H__

#include "IEcoBase1.h"
#include "IEcoGGUF1File.h"
#include "IEcoGGUF1TensorInfo.h"
#include "IEcoGGUF1MetadataKV.h"
#include "IEcoGGUF1MetadataValue.h"
#include "IEcoRawData1.h"

/* IEcoGGUF1 IID = {17B59DBD-0DCC-4EB7-B54A-467B3AF85CA8} */
#ifndef __IID_IEcoGGUF1
static const UGUID IID_IEcoGGUF1 = {0x01, 0x10, {0x17, 0xB5, 0x9D, 0xBD, 0x0D, 0xCC, 0x4E, 0xB7, 0xB5, 0x4A, 0x46, 0x7B, 0x3A, 0xF8, 0x5C, 0xA8}};
#endif

typedef struct IEcoGGUF1* IEcoGGUF1Ptr_t;

typedef struct IEcoGGUF1VTbl {
    int16_t (ECOCALLMETHOD *QueryInterface)(IEcoGGUF1Ptr_t me, const UGUID* riid, voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(IEcoGGUF1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(IEcoGGUF1Ptr_t me);

    IEcoGGUF1File* (ECOCALLMETHOD *readFile)(IEcoGGUF1Ptr_t me, char_t* fileName);
    int16_t (ECOCALLMETHOD *writeFile)(IEcoGGUF1Ptr_t me, IEcoGGUF1File* pIFile, char_t* fileName);
    IEcoGGUF1File* (ECOCALLMETHOD *readFileFromMemory)(IEcoGGUF1Ptr_t me, byte_t* ptr, uint64_t size);
    int16_t (ECOCALLMETHOD *writeFileToMemory)(IEcoGGUF1Ptr_t me, IEcoGGUF1File* pIFile, byte_t** ptr, uint64_t* size);

    IEcoGGUF1File* (ECOCALLMETHOD *createFile)(IEcoGGUF1Ptr_t me);
    IEcoGGUF1TensorInfo* (ECOCALLMETHOD *createTensorInfo)(IEcoGGUF1Ptr_t me);
    IEcoGGUF1MetadataKV* (ECOCALLMETHOD *createMetadataKV)(IEcoGGUF1Ptr_t me);
    IEcoGGUF1MetadataValue* (ECOCALLMETHOD *createMetadataValue)(IEcoGGUF1Ptr_t me);
    IEcoRawData1* (ECOCALLMETHOD *createRawData)(IEcoGGUF1Ptr_t me);
} IEcoGGUF1VTbl, *IEcoGGUF1VTblPtr;

interface IEcoGGUF1 {
    struct IEcoGGUF1VTbl* pVTbl;
} IEcoGGUF1;

#endif /* __I_ECO_GGUF_1_H__ */
