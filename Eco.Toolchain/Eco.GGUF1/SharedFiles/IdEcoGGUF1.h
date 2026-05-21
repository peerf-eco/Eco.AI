#ifndef __ID_ECO_GGUF_1_H__
#define __ID_ECO_GGUF_1_H__

#include "IEcoBase1.h"
#include "IEcoGGUF1.h"

/* EcoGGUF1 CID = {A1C53A77-9BCB-4AD7-8B63-4F1A6EAA44B1} */
#ifndef __CID_EcoGGUF1
static const UGUID CID_EcoGGUF1 = {0x01, 0x10, {0xA1, 0xC5, 0x3A, 0x77, 0x9B, 0xCB, 0x4A, 0xD7, 0x8B, 0x63, 0x4F, 0x1A, 0x6E, 0xAA, 0x44, 0xB1}};
#endif

#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#elif ECO_LIB
extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_A1C53A779BCB4AD78B634F1A6EAA44B1;
#endif

#endif /* __ID_ECO_GGUF_1_H__ */
