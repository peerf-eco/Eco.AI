#ifndef __C_ECO_GGUF_1_FILE_H__
#define __C_ECO_GGUF_1_FILE_H__

#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"
#include "IEcoGGUF1File.h"

typedef struct CEcoGGUF1_6EAA44B1File {
    IEcoGGUF1FileVTbl* m_pVTblIFile;
    uint32_t m_cRef;
    IEcoMemoryAllocator1* m_pIMem;
    IEcoSystem1* m_pISys;
    ECO_GGUF1_HEADER_DESCRIPTOR m_Descriptor;
    uint32_t m_Alignment;
    IEcoList1* m_pIMetadataKVs;
    IEcoList1* m_pITensorInfos;
    IEcoUnknown* m_pITensorData;
    char_t* m_TensorDataSourcePath;
    uint64_t m_TensorDataSourceOffset;
    uint64_t m_TensorDataSourceSize;
} CEcoGGUF1_6EAA44B1File, *CEcoGGUF1_6EAA44B1FilePtr;

int16_t ECOCALLMETHOD createCEcoGGUF1_6EAA44B1File(IEcoUnknown* pIUnkSystem, IEcoUnknown* pIUnkOuter, IEcoGGUF1File** ppIFile);
void ECOCALLMETHOD deleteCEcoGGUF1_6EAA44B1File(IEcoGGUF1File* pIFile);

#endif /* __C_ECO_GGUF_1_FILE_H__ */
