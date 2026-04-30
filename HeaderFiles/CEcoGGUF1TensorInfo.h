#ifndef __C_ECO_GGUF_1_TENSOR_INFO_H__
#define __C_ECO_GGUF_1_TENSOR_INFO_H__

#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"
#include "IdEcoString1.h"
#include "IEcoGGUF1TensorInfo.h"

typedef struct CEcoGGUF1_6EAA44B1TensorInfo {
    IEcoGGUF1TensorInfoVTbl* m_pVTblITensorInfo;
    uint32_t m_cRef;
    IEcoMemoryAllocator1* m_pIMem;
    IEcoSystem1* m_pISys;
    IEcoString1* m_pIStr;
    ECO_GGUF1_TENSOR_INFO_DESCRIPTOR m_Descriptor;
    IEcoUnknown* m_pIRawData;
} CEcoGGUF1_6EAA44B1TensorInfo, *CEcoGGUF1_6EAA44B1TensorInfoPtr;

int16_t ECOCALLMETHOD createCEcoGGUF1_6EAA44B1TensorInfo(IEcoUnknown* pIUnkSystem, IEcoUnknown* pIUnkOuter, IEcoGGUF1TensorInfo** ppIInfo);
void ECOCALLMETHOD deleteCEcoGGUF1_6EAA44B1TensorInfo(IEcoGGUF1TensorInfo* pIInfo);

#endif /* __C_ECO_GGUF_1_TENSOR_INFO_H__ */
