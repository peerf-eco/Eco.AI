#ifndef __C_ECO_GGUF_1_RAW_DATA_H__
#define __C_ECO_GGUF_1_RAW_DATA_H__

#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"
#include "IEcoRawData1.h"

typedef struct CEcoGGUF1_6EAA44B1RawData {
    IEcoRawData1VTbl* m_pVTblIRawData;
    uint32_t m_cRef;
    IEcoMemoryAllocator1* m_pIMem;
    IEcoSystem1* m_pISys;
    byte_t* m_pData;
    uint32_t m_Size;
} CEcoGGUF1_6EAA44B1RawData, *CEcoGGUF1_6EAA44B1RawDataPtr;

int16_t ECOCALLMETHOD createCEcoGGUF1_6EAA44B1RawData(IEcoUnknown* pIUnkSystem, IEcoUnknown* pIUnkOuter, IEcoRawData1** ppIRawData);
void ECOCALLMETHOD deleteCEcoGGUF1_6EAA44B1RawData(IEcoRawData1* pIRawData);

#endif /* __C_ECO_GGUF_1_RAW_DATA_H__ */
