/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoThreadManager1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoThreadManager1
 * </описание>
 *
 * <ссылка>
 *
 * </ссылка>
 *
 * <автор>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_THREAD_1_H__
#define __I_ECO_THREAD_1_H__

#include "IEcoBase1.h"

#ifndef ThreadProc
typedef uint32_t (*ThreadProc)(/* in */ IEcoUnknown*, /* in */ void*);
#endif

/* IEcoThread1 IID = {D300728A-3F0C-4721-A9F1-7F393C90E9BF} */
#ifndef __IID_IEcoThread1
static const UGUID IID_IEcoThread1 = {0x01, 0x10, {0xD3, 0x00, 0x72, 0x8A, 0x3F, 0x0C, 0x47, 0x21, 0xA9, 0xF1, 0x7F, 0x39, 0x3C, 0x90, 0xE9, 0xBF} };
#endif /* __IID_IEcoThread1 */

typedef struct IEcoThread1* IEcoThread1Ptr_t;

typedef struct IEcoThread1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoThread1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoThread1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoThread1Ptr_t me);

    /* IEcoThread1 */
    uint32_t (ECOCALLMETHOD *get_Id)(/* in */ IEcoThread1Ptr_t me);
    IEcoUnknown* (ECOCALLMETHOD *get_OwnerProcess)(/* in */ IEcoThread1Ptr_t me);
    void (ECOCALLMETHOD *Sleep)(/* in */ IEcoThread1Ptr_t me, /* in */ int32_t Milliseconds);
    bool_t (ECOCALLMETHOD *Switch)(/* in */ IEcoThread1Ptr_t me);
    void (ECOCALLMETHOD *Exit)(/* in */ IEcoThread1Ptr_t me, /* in */ int16_t exitCode);

} IEcoThread1VTbl, *IEcoThread1VTblPtr;

interface IEcoThread1 {
    struct IEcoThread1VTbl *pVTbl;
} IEcoThread1;

#endif /* __I_ECO_THREAD_1_H__ */
