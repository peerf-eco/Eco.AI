/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoError1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoError
 * 
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_ERROR_1_H__
#define __I_ECO_ERROR_1_H__

#include "IEcoBase1.h"

/* IEcoError1 IID = 00000000-0000-0000-0000-00000000FFFE */
#ifndef __IID_IEcoError1
static const UGUID IID_IEcoError1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFE} };
#endif /* __IID_IEcoError1 */

#ifndef ECO_I_ECO_ERROR_1_PTR_T_DEFINED
typedef struct IEcoError1* IEcoError1Ptr_t;
#define ECO_I_ECO_ERROR_1_PTR_T_DEFINED
#endif

typedef struct IEcoError1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoError1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoError1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoError1Ptr_t me);

    /* IEcoError1 */
    void (ECOCALLMETHOD *set_ErrorMode)(/* in */ IEcoError1Ptr_t me, /* in */ uint16_t errMode);
    uint16_t (ECOCALLMETHOD *get_ErrorMode)(/* in */ IEcoError1Ptr_t me);
    void (ECOCALLMETHOD *set_LastError)(/* in */ IEcoError1Ptr_t me, /* in */ int16_t errCode);
    int16_t (ECOCALLMETHOD *get_LastError)(/* in */ IEcoError1Ptr_t me);
    int16_t (ECOCALLMETHOD *get_Description)(/* in */ IEcoError1Ptr_t me, /* in */ int16_t errCode, /* in | out */ voidptr_t pvMessage, /* in | out */ uint16_t* iSize);

} IEcoError1VTbl, *IEcoError1VTblPtr;

interface IEcoError1 {
    struct IEcoError1VTbl *pVTbl;
} IEcoError1;

#endif /* __I_ECO_ERROR_1_H__ */
