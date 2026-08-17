/*
 * <кодировка символов>
 *   Cyrillic (Windows) - Codepage 1251
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoLog1SimpleLayout
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoLog1SimpleLayout
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

#ifndef __I_ECO_LOG_1_SIMPLE_LAYOUT_HPP__
#define __I_ECO_LOG_1_SIMPLE_LAYOUT_HPP__

#include "IEcoBase1.hpp"
#include "IEcoLog1.hpp"

/* IEcoLog1SimpleLayout IID = {9485C6A5-2CBF-4D46-B8B5-94F60740BEE3} */
#ifndef __IID_IEcoLog1SimpleLayout
static const UGUID IID_IEcoLog1SimpleLayout = {0x01, 0x10, 0x94, 0x85, 0xC6, 0xA5, 0x2C, 0xBF, 0x4D, 0x46, 0xB8, 0xB5, 0x94, 0xF6, 0x07, 0x40, 0xBE, 0xE3};
#endif /* __IID_IEcoLog1SimpleLayout */

interface IEcoLog1SimpleLayout : public IEcoUnknown {

    /* IEcoLog1SimpleLayout */
    virtual char_t* ECOCALLMETHOD get_Name(/* in */ void) = 0;
    virtual char_t* ECOCALLMETHOD Format(/* in */ uint16_t level, /* in */ char_t* data, /* in */ uint32_t size) = 0;

    /* IEcoLog1SimpleLayout */
    virtual char_t* ECOCALLMETHOD get_Pattern(/* in */ void) = 0;
    virtual void ECOCALLMETHOD set_Pattern( /* in */ char_t* name) = 0;

};

#endif /* __I_ECO_LOG_1_SIMPLE_LAYOUT_HPP__ */

