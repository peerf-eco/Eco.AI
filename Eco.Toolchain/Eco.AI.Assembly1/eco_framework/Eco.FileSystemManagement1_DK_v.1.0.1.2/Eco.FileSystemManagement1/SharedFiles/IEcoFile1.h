/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoFile1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoFile1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_FILE_1_H__
#define __I_ECO_FILE_1_H__

#include "IEcoBase1.h"
#include "IEcoFileInfo1.h"

/* IEcoFile1 IID = {00000000-0000-0000-0000-C00000000104} */
#ifndef __IID_IEcoFile1
static const UGUID IID_IEcoFile1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x01, 0x04 } };
#endif /* __IID_IEcoFile1 */

typedef struct IEcoFile1* IEcoFile1Ptr_t;

typedef struct IEcoFile1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface )(/* in */ IEcoFile1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef )(/* in */ IEcoFile1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release )(/* in */ IEcoFile1Ptr_t me);

    /* IEcoFile1 */
    uint32_t (ECOCALLMETHOD *get_Size)(/* in */ IEcoFile1Ptr_t me);
    char_t* (ECOCALLMETHOD *get_Name)(/* in */ IEcoFile1Ptr_t me);
    IEcoFileInfo1* (ECOCALLMETHOD *get_Info)(/* in */ IEcoFile1Ptr_t me);
    uint32_t (ECOCALLMETHOD *get_Pointer)(/* in */ IEcoFile1Ptr_t me);
    void (ECOCALLMETHOD *set_Pointer)(/* in */ IEcoFile1Ptr_t me, /* in */ uint32_t value);
    int16_t (ECOCALLMETHOD *Read)(/* in */ IEcoFile1Ptr_t me, /* in */ voidptr_t pv, /* in | out */ uint32_t* pSize);
    int16_t (ECOCALLMETHOD *Write)(/* in */ IEcoFile1Ptr_t me, /* in */ voidptr_t pv, /* in | out */ uint32_t* pSize);
    int16_t (ECOCALLMETHOD *Close)(/* in */ IEcoFile1Ptr_t me);
    descriptor_t (ECOCALLMETHOD *get_Descriptor)(/* in */ IEcoFile1Ptr_t me);

} IEcoFile1VTbl, *IEcoFile1VTblPtr;

interface IEcoFile1 {
    struct IEcoFile1VTbl *pVTbl;
} IEcoFile1;

#endif /* __I_ECO_FILE_1_H__ */
