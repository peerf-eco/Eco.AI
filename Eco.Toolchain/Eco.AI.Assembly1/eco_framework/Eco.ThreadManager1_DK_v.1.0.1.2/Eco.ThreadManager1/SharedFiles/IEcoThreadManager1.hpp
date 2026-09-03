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

#ifndef __I_ECO_THREAD_MANAGER_1_HPP__
#define __I_ECO_THREAD_MANAGER_1_HPP__

#include "IEcoBase1.hpp"
#include "IEcoThread1.hpp"

/* IEcoThreadManager1 IID = {E6ACB432-EBD4-4607-BE6E-0C1F0A49D6B5} */
#ifndef __IID_IEcoThreadManager1
static const UGUID IID_IEcoThreadManager1 = {0x01, 0x10, {0xE6, 0xAC, 0xB4, 0x32, 0xEB, 0xD4, 0x46, 0x07, 0xBE, 0x6E, 0x0C, 0x1F, 0x0A, 0x49, 0xD6, 0xB5}};
#endif /* __IID_IEcoThreadManager1 */

interface IEcoThreadManager1 : public IEcoUnknown {
public:
    /* IEcoThreadManager1 */
    virtual IEcoThread1* ECOCALLMETHOD get_CurrentThread(/* in*/ void) = 0;
    virtual IEcoThread1* ECOCALLMETHOD CreateThread(/* in */ ThreadProc func, /* in */ void* param, /* in */ uint32_t stackSize, /* in */ bool_t bSuspended) = 0;
    virtual int16_t ECOCALLMETHOD TerminateThread(/* in */ IEcoThread1* pIThread, /* in */ uint32_t iExitCode) = 0;
    virtual int16_t ECOCALLMETHOD SuspendThread(/* in */ IEcoThread1* pIThread) = 0;
    virtual int16_t ECOCALLMETHOD ResumeThread(/* in */ IEcoThread1* pIThread) = 0;

};

#endif /* __I_ECO_THREAD_MANAGER_1_HPP__ */
