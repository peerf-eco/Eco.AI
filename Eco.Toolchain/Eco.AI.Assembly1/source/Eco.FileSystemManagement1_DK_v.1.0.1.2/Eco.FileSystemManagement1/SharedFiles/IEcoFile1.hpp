/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoFile1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoFile1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_FILE_1_HPP__
#define __I_ECO_FILE_1_HPP__

#include "IEcoBase1.hpp"
#include "IEcoFileInfo1.hpp"

/* IEcoFile1 IID = {00000000-0000-0000-0000-C00000000104} */
#ifndef __IID_IEcoFile1
static const UGUID IID_IEcoFile1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x01, 0x04 } };
#endif /* __IID_IEcoFile1 */

interface IEcoFile1 : public IEcoUnknown {
public:
    /* IEcoFile1 */
    virtual uint32_t ECOCALLMETHOD get_Size(/* in*/ void) = 0;
    virtual char_t* ECOCALLMETHOD get_Name(/* in*/ void) = 0;
    virtual IEcoFileInfo1* ECOCALLMETHOD get_Info(/* in*/ void) = 0;
    virtual uint32_t ECOCALLMETHOD get_Pointer(/* in*/ void) = 0;
    virtual void ECOCALLMETHOD set_Pointer(/* in */ uint32_t value) = 0;
    virtual int16_t ECOCALLMETHOD Read(/* in */ voidptr_t pv, /* in | out */ uint32_t* pSize) = 0;
    virtual int16_t ECOCALLMETHOD Write(/* in */ voidptr_t pv, /* in | out */ uint32_t* pSize) = 0;
    virtual int16_t ECOCALLMETHOD Close(/* in*/ void) = 0;
    virtual descriptor_t ECOCALLMETHOD get_Descriptor(/* in*/ void) = 0;

};

#endif /* __I_ECO_FILE_1_HPP__ */
