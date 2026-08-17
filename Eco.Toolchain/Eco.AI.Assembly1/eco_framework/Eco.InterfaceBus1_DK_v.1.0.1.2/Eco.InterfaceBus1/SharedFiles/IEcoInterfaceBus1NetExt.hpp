/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoInterfaceBus1NetExt
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoInterfaceBus1NetExt
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_INTERFACE_BUS_1_EXTENSION_HPP__
#define __I_ECO_INTERFACE_BUS_1_EXTENSION_HPP__

#include "IEcoBase1.hpp"

/* IEcoInterfaceBus1NetExt IID = {00000000-0000-0000-0000-A00300000101} */
#ifndef __IID_IEcoInterfaceBus1NetExt
static const UGUID IID_IEcoInterfaceBus1NetExt = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xA0, 0x03, 0x00, 0x00, 0x01, 0x01}};
#endif /* __IID_IEcoInterfaceBus1NetExt */

interface IEcoInterfaceBus1NetExt : public IEcoUnknown {
public:
    virtual int16_t ECOCALLMETHOD set_Manager(/*in*/ const UGUID* rcid) = 0;
    virtual const UGUID* ECOCALLMETHOD get_Manager(/*in*/ void) = 0;
    virtual int16_t ECOCALLMETHOD QueryComponent(/*in*/ char_t* networkname, /*in*/ const UGUID* rcid, /*in*/ IEcoUnknown* pIUnkOuter, /*in*/ const UGUID* riid, /*out*/ voidptr_t* ppv) = 0;

};

#endif /* __I_ECO_INTERFACE_BUS_1_EXTENSION_HPP__ */
