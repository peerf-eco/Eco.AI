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

#ifndef __I_ECO_THREAD_MANAGER_1_H__
#define __I_ECO_THREAD_MANAGER_1_H__

#include "IEcoBase1.h"
#include "IEcoThread1.h"

/* IEcoThreadManager1 IID = {E6ACB432-EBD4-4607-BE6E-0C1F0A49D6B5} */
#ifndef __IID_IEcoThreadManager1
static const UGUID IID_IEcoThreadManager1 = {0x01, 0x10, {0xE6, 0xAC, 0xB4, 0x32, 0xEB, 0xD4, 0x46, 0x07, 0xBE, 0x6E, 0x0C, 0x1F, 0x0A, 0x49, 0xD6, 0xB5}};
#endif /* __IID_IEcoThreadManager1 */

typedef struct IEcoThreadManager1* IEcoThreadManager1Ptr_t;

typedef struct IEcoThreadManager1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoThreadManager1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoThreadManager1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoThreadManager1Ptr_t me);

    /* IEcoThreadManager1 */
    IEcoThread1Ptr_t (ECOCALLMETHOD *get_CurrentThread)(/* in */ IEcoThreadManager1Ptr_t me);
    IEcoThread1Ptr_t (ECOCALLMETHOD *CreateThread)(/* in */ IEcoThreadManager1Ptr_t me, /* in */ ThreadProc func, /* in */ void* param, /* in */ uint32_t stackSize, /* in */ bool_t bSuspended);
    int16_t (ECOCALLMETHOD *TerminateThread)(/* in */ IEcoThreadManager1Ptr_t me, /* in */ IEcoThread1* pIThread, /* in */ uint32_t iExitCode);
    int16_t (ECOCALLMETHOD *SuspendThread)(/* in */ IEcoThreadManager1Ptr_t me, /* in */ IEcoThread1* pIThread);
    int16_t (ECOCALLMETHOD *ResumeThread)(/* in */ IEcoThreadManager1Ptr_t me, /* in */ IEcoThread1* pIThread);

} IEcoThreadManager1VTbl, *IEcoThreadManager1VTblPtr;

interface IEcoThreadManager1 {
    struct IEcoThreadManager1VTbl *pVTbl;
} IEcoThreadManager1;

#endif /* __I_ECO_THREAD_MANAGER_1_H__ */
