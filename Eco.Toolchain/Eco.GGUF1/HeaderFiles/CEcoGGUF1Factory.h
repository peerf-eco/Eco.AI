#ifndef __C_ECOGGUF1_FACTORY_H__
#define __C_ECOGGUF1_FACTORY_H__

#include "IEcoSystem1.h"

typedef struct CEcoGGUF1_6EAA44B1Factory {
    IEcoComponentFactoryVTbl* m_pVTblICF;
    uint32_t m_cRef;
    CreateInstance m_pInstance;
    InitInstance m_pInitInstance;
    char_t m_Name[64];
    char_t m_Version[16];
    char_t m_Manufacturer[64];
} CEcoGGUF1_6EAA44B1Factory;

#endif /* __C_ECOGGUF1_FACTORY_H__ */
