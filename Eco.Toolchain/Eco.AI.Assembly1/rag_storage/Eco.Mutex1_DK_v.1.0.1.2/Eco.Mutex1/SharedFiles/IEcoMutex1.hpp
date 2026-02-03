/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoMutex1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoMutex1
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

#ifndef __I_ECO_MUTEX_1_HPP__
#define __I_ECO_MUTEX_1_HPP__

#include "IEcoBase1.hpp"

/* IEcoMutex1 IID = {DD292B8D-750B-4A3C-BB8D-316D609A398A} */
#ifndef __IID_IEcoMutex1
static const UGUID IID_IEcoMutex1 = {0x01, 0x10, {0xDD, 0x29, 0x2B, 0x8D, 0x75, 0x0B, 0x4A, 0x3C, 0xBB, 0x8D, 0x31, 0x6D, 0x60, 0x9A, 0x39, 0x8A} };
#endif /* __IID_IEcoMutex1 */

interface IEcoMutex1 : public IEcoUnknown {
public:
    /* IEcoMutex1 */
    virtual void ECOCALLMETHOD Lock(/* in*/ void) = 0;
    virtual void ECOCALLMETHOD UnLock(/* in*/ void) = 0;

};

#endif /* __I_ECO_MUTEX_1_HPP__ */
