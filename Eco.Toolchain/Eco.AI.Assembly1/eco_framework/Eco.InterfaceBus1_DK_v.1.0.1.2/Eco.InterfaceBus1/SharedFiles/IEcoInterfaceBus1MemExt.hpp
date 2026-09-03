/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoInterfaceBus1MemExt
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoInterfaceBus1MemExt
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_INTERFACE_BUS_1_MEMORY_EXTENSION_HPP__
#define __I_ECO_INTERFACE_BUS_1_MEMORY_EXTENSION_HPP__

#include "IEcoBase1.hpp"

/* IEcoInterfaceBus1MemExt IID = {00000000-0000-0000-0000-A00100000101} */
#ifndef __IID_IEcoInterfaceBus1MemExt
static const UGUID IID_IEcoInterfaceBus1MemExt = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xA0, 0x01, 0x00, 0x00, 0x01, 0x01} };
#endif /* __IID_IEcoInterfaceBus1MemExt */

interface IEcoInterfaceBus1MemExt : public IEcoUnknown {
public:
    virtual int16_t ECOCALLMETHOD set_Manager(/*in*/ const UGUID* rcid) = 0;
    virtual const UGUID* ECOCALLMETHOD get_Manager(/*in*/ void) = 0;
    virtual int16_t ECOCALLMETHOD set_ExpandPool(/*in*/ bool_t bExpandPool) = 0;

};

#endif /* __I_ECO_INTERFACE_BUS_1_MEMORY_EXTENSION_HPP__ */
