#ifndef __I_ECO_RAW_DATA_1_H__
#define __I_ECO_RAW_DATA_1_H__

#include "IEcoBase1.h"

/* IEcoRawData1 IID = {E532E7FC-3578-4E61-A528-D5397B0F8D98} */
#ifndef __IID_IEcoRawData1
static const UGUID IID_IEcoRawData1 = {0x01, 0x10, {0xE5, 0x32, 0xE7, 0xFC, 0x35, 0x78, 0x4E, 0x61, 0xA5, 0x28, 0xD5, 0x39, 0x7B, 0x0F, 0x8D, 0x98}};
#endif

typedef struct IEcoRawData1* IEcoRawData1Ptr_t;

typedef struct IEcoRawData1VTbl {
    int16_t (ECOCALLMETHOD *QueryInterface)(IEcoRawData1Ptr_t me, const UGUID* riid, voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(IEcoRawData1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(IEcoRawData1Ptr_t me);

    byte_t* (ECOCALLMETHOD *Alloc)(IEcoRawData1Ptr_t me, uint32_t size);
    void (ECOCALLMETHOD *Fill)(IEcoRawData1Ptr_t me, byte_t value);
    void (ECOCALLMETHOD *Free)(IEcoRawData1Ptr_t me);
    uint32_t (ECOCALLMETHOD *get_Size)(IEcoRawData1Ptr_t me);
    byte_t* (ECOCALLMETHOD *get_Pointer)(IEcoRawData1Ptr_t me, uint32_t offset);
} IEcoRawData1VTbl, *IEcoRawData1VTblPtr;

interface IEcoRawData1 {
    struct IEcoRawData1VTbl* pVTbl;
} IEcoRawData1;

#endif /* __I_ECO_RAW_DATA_1_H__ */
