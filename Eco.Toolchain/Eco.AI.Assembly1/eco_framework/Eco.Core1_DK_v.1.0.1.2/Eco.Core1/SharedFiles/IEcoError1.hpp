/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoError1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoError
 * 
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_ERROR_1_HPP__
#define __I_ECO_ERROR_1_HPP__

#include "IEcoBase1.hpp"

/* IEcoError1 IID = 00000000-0000-0000-0000-00000000FFFE */
#ifndef __IID_IEcoError1
static const UGUID IID_IEcoError1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFE} };
#endif /* __IID_IEcoError1 */

interface IEcoError1 : public IEcoUnknown {
public:
    /* IEcoError1 */
    virtual void ECOCALLMETHOD set_ErrorMode(/* in */ uint16_t errMode) = 0;
    virtual uint16_t ECOCALLMETHOD get_ErrorMode(/* in */ void) = 0;
    virtual void ECOCALLMETHOD set_LastError(/* in */ int16_t errCode) = 0;
    virtual int16_t ECOCALLMETHOD get_LastError(/* in */ void) = 0;
    virtual int16_t ECOCALLMETHOD get_Description(/* in */ int16_t errCode, /* in | out */ voidptr_t pvMessage, /* in | out */ uint16_t* iSize) = 0;

};

#endif /* __I_ECO_ERROR_1_HPP__ */
