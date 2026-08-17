/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoInterfaceBus1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoInterfaceBus1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_INTERFACE_BUS_1_HPP__
#define __I_ECO_INTERFACE_BUS_1_HPP__

#include "IEcoBase1.hpp"

/* IEcoInterfaceBus1 IID = {00000000-0000-0000-0000-A00000000101} */
#ifndef __IID_IEcoInterfaceBus1
static const UGUID IID_IEcoInterfaceBus1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xA0, 0x00, 0x00, 0x00, 0x01, 0x01} };
#endif /* __IID_IEcoInterfaceBus1 */

interface IEcoInterfaceBus1 : public IEcoUnknown {
public:
    /* IEcoInterfaceBus1 */
    virtual int16_t ECOCALLMETHOD Init(/*in*/ void) = 0;
    virtual int16_t ECOCALLMETHOD InitWith(/*in*/ void* heapStartAddress, /*in*/ uint32_t size) = 0;
    virtual int16_t ECOCALLMETHOD RegisterComponent(/*in*/ const UGUID* rcid, /*in*/ IEcoUnknown* pIFactory) = 0;
    virtual int16_t ECOCALLMETHOD UnRegisterComponent(/*in*/ const UGUID* rcid) = 0;
    virtual int16_t ECOCALLMETHOD QueryComponent(/*in*/ const UGUID* rcid, /*in*/ IEcoUnknown* pIUnkOuter, /*in*/ const UGUID* riid, /*out*/ voidptr_t* ppv) = 0;

};

#endif /* __I_ECO_INTERFACE_BUS_1_HPP__ */
