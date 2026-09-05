#ifndef __C_ECO_GGUF_1_METADATA_VALUE_H__
#define __C_ECO_GGUF_1_METADATA_VALUE_H__

#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"
#include "IdEcoString1.h"
#include "IEcoGGUF1MetadataValue.h"

typedef struct CEcoGGUF1_6EAA44B1MetadataValue {
    IEcoGGUF1MetadataValueVTbl* m_pVTblIMetadataValue;
    uint32_t m_cRef;
    IEcoMemoryAllocator1* m_pIMem;
    IEcoSystem1* m_pISys;
    IEcoString1* m_pIStr;
    ECO_GGUF1_METADATA_VALUE_DESCRIPTOR m_Descriptor;
    IEcoList1* m_pIArrayItems;
} CEcoGGUF1_6EAA44B1MetadataValue, *CEcoGGUF1_6EAA44B1MetadataValuePtr;

int16_t ECOCALLMETHOD createCEcoGGUF1_6EAA44B1MetadataValue(IEcoUnknown* pIUnkSystem, IEcoUnknown* pIUnkOuter, IEcoGGUF1MetadataValue** ppIValue);
void ECOCALLMETHOD deleteCEcoGGUF1_6EAA44B1MetadataValue(IEcoGGUF1MetadataValue* pIValue);

#endif /* __C_ECO_GGUF_1_METADATA_VALUE_H__ */
