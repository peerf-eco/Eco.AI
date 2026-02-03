/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoSystemInformation1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoSystemInformation1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_SYSTEM_INFORMATION_1_H__
#define __I_ECO_SYSTEM_INFORMATION_1_H__

#include "IEcoBase1.h"

/* IEcoSystemInformation1 IID = {00000000-0000-0000-0000-0000000001FF} */
#ifndef __IID_IEcoSystemInformation1
static const UGUID IID_IEcoSystemInformation1 = {0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0xFF}};
#endif /* __IID_IEcoSystemInformation1 */

typedef struct IEcoSystemInformation1* IEcoSystemInformation1Ptr_t;

typedef struct IEcoSystemInformation1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoSystemInformation1Ptr_t me, /* in */ const UGUID* riid, /* out */ void **ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoSystemInformation1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoSystemInformation1Ptr_t me);

    /* IEcoSystemInformation1 */
    char_t* (ECOCALLMETHOD *get_Name)(/* in */IEcoSystemInformation1Ptr_t me);
    char_t* (ECOCALLMETHOD *get_Id)(/* in */ IEcoSystemInformation1Ptr_t me);

} IEcoSystemInformation1VTbl, *IEcoSystemInformation1VTblPtr;

interface IEcoSystemInformation1 {
    struct IEcoSystemInformation1VTbl *pVTbl;
} IEcoSystemInformation1;

#endif /* __I_ECO_SYSTEM_INFORMATION_1_H__ */
