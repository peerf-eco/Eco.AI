/*
 * <кодировка символов>
 *   Cyrillic (Windows) - Codepage 1251
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoLog1ConsoleAffiliate
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoLog1ConsoleAffiliate
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

#ifndef __I_ECO_LOG_1_CONSOLE_AFFILIATE_HPP__
#define __I_ECO_LOG_1_CONSOLE_AFFILIATE_HPP__

#include "IEcoBase1.hpp"
#include "IEcoLog1.hpp"

/* IEcoLog1ConsoleAffiliate IID = {FECB29A2-3D60-4501-9F83-47C4752CFA3A} */
#ifndef __IID_IEcoLog1ConsoleAffiliate
static const UGUID IID_IEcoLog1ConsoleAffiliate = {0x01, 0x10, 0xFE, 0xCB, 0x29, 0xA2, 0x3D, 0x60, 0x45, 0x01, 0x9F, 0x83, 0x47, 0xC4, 0x75, 0x2C, 0xFA, 0x3A};
#endif /* __IID_IEcoLog1ConsoleAffiliate */

interface IEcoLog1ConsoleAffiliate : public IEcoUnknown{

    /* IEcoLog1Affiliate */
    virtual char_t* ECOCALLMETHOD get_Name(/* in */ void) = 0;
    virtual IEcoLog1Layout* ECOCALLMETHOD get_Layout(/* in */ void) = 0;
    virtual void ECOCALLMETHOD set_Layout(/* in */ IEcoLog1Layout* pILayout) = 0;
    virtual int16_t ECOCALLMETHOD Write(/* in */ uint16_t level, /* in */ char_t* data, /* in */ uint32_t size) = 0;

    /* IEcoLog1ConsoleAffiliate */
    virtual char_t* ECOCALLMETHOD get_TargetOutput(/* in */ void) = 0;
    virtual void ECOCALLMETHOD set_TargetOutput(/* in */ char_t* name) = 0;

};

#endif /* __I_ECO_LOG_1_CONSOLE_AFFILIATE_HPP__ */

