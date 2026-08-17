/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoInterfaceBus1FileExt
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoInterfaceBus1FileExt
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_INTERFACE_BUS_1_FILE_EXTENSION_HPP__
#define __I_ECO_INTERFACE_BUS_1_FILE_EXTENSION_HPP__

#include "IEcoBase1.hpp"

/* IEcoInterfaceBus1FileExt IID = {00000000-0000-0000-0000-A00200000101} */
#ifndef __IID_IEcoInterfaceBus1FileExt
static const UGUID IID_IEcoInterfaceBus1FileExt = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xA0, 0x02, 0x00, 0x00, 0x01, 0x01} };
#endif /* __IID_IEcoInterfaceBus1FileExt */

interface IEcoInterfaceBus1FileExt : public IEcoUnknown {
public:
    /* IEcoInterfaceBus1 */
    virtual int16_t ECOCALLMETHOD set_Manager(/*in*/ const UGUID* rcid) = 0;
    virtual const UGUID* ECOCALLMETHOD get_Manager(/*in*/ void) = 0;
    virtual int16_t ECOCALLMETHOD set_SearchPath(/*in*/ char_t* path) = 0;
    virtual char_t* ECOCALLMETHOD get_SearchPath(/*in*/ void) = 0;
    virtual int16_t ECOCALLMETHOD RegisterComponent(/*in*/ const UGUID* rcid, /*in*/ char_t* filename) = 0;
    virtual int16_t ECOCALLMETHOD QueryComponent(/*in*/ char_t* filename, /*in*/ const UGUID* rcid, /*in*/ IEcoUnknown* pIUnkOuter, /*in*/ const UGUID* riid, /*out*/ voidptr_t* ppv) = 0;

};

#endif /* __I_ECO_INTERFACE_BUS_1_FILE_EXTENSION_HPP__ */
