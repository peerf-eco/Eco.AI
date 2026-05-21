#ifndef __C_ECO_GGUF_1_H__
#define __C_ECO_GGUF_1_H__

#include "IEcoGGUF1.h"
#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"
#include "IdEcoString1.h"
#include "IdEcoInterfaceBus1.h"
#include "IdEcoFileSystemManagement1.h"

typedef struct CEcoGGUF1_6EAA44B1 {
    IEcoGGUF1VTbl* m_pVTblIGGUF1;
    uint32_t m_cRef;
    IEcoMemoryAllocator1* m_pIMem;
    IEcoSystem1* m_pISys;
    IEcoInterfaceBus1* m_pIBus;
    IEcoString1* m_pIStr;
    IEcoFileManager1* m_pIFileMgr;
} CEcoGGUF1_6EAA44B1, *CEcoGGUF1_6EAA44B1Ptr;

int16_t ECOCALLMETHOD initCEcoGGUF1_6EAA44B1(IEcoGGUF1Ptr_t me, IEcoUnknownPtr_t pIUnkSystem);
int16_t ECOCALLMETHOD createCEcoGGUF1_6EAA44B1(IEcoUnknownPtr_t pIUnkSystem, IEcoUnknownPtr_t pIUnkOuter, IEcoGGUF1Ptr_t* ppIGGUF1);
void ECOCALLMETHOD deleteCEcoGGUF1_6EAA44B1(IEcoGGUF1Ptr_t pIGGUF1);

#endif /* __C_ECO_GGUF_1_H__ */
