#ifndef __C_ECO_GGUF_1_METADATA_KV_H__
#define __C_ECO_GGUF_1_METADATA_KV_H__

#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"
#include "IdEcoString1.h"
#include "IEcoGGUF1MetadataKV.h"

typedef struct CEcoGGUF1_6EAA44B1MetadataKV {
    IEcoGGUF1MetadataKVVTbl* m_pVTblIMetadataKV;
    uint32_t m_cRef;
    IEcoMemoryAllocator1* m_pIMem;
    IEcoSystem1* m_pISys;
    IEcoString1* m_pIStr;
    ECO_GGUF1_METADATA_KV_DESCRIPTOR m_Descriptor;
    IEcoGGUF1MetadataValue* m_pIValue;
} CEcoGGUF1_6EAA44B1MetadataKV, *CEcoGGUF1_6EAA44B1MetadataKVPtr;

int16_t ECOCALLMETHOD createCEcoGGUF1_6EAA44B1MetadataKV(IEcoUnknown* pIUnkSystem, IEcoUnknown* pIUnkOuter, IEcoGGUF1MetadataKV** ppIKV);
void ECOCALLMETHOD deleteCEcoGGUF1_6EAA44B1MetadataKV(IEcoGGUF1MetadataKV* pIKV);

#endif /* __C_ECO_GGUF_1_METADATA_KV_H__ */
