/*
 * <кодировка символов>
 *   Cyrillic (Windows) - Codepage 1251
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoLog1FileAffiliate
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoLog1FileAffiliate
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

#ifndef __I_ECO_LOG_1_FILE_AFFILIATE_HPP__
#define __I_ECO_LOG_1_FILE_AFFILIATE_HPP__

#include "IEcoBase1.hpp"
#include "IEcoLog1.hpp"

/* IEcoLog1FileAffiliate IID = {22B0B071-478D-461A-9F5B-5F40D4D79B7A} */
#ifndef __IID_IEcoLog1FileAffiliate
static const UGUID IID_IEcoLog1FileAffiliate = {0x01, 0x10, 0x22, 0xB0, 0xB0, 0x71, 0x47, 0x8D, 0x46, 0x1A, 0x9F, 0x5B, 0x5F, 0x40, 0xD4, 0xD7, 0x9B, 0x7A};
#endif /* __IID_IEcoLog1FileAffiliate */

interface IEcoLog1FileAffiliate : public IEcoUnknown {

    /* IEcoLog1Affiliate */
    virtual char_t* ECOCALLMETHOD get_Name(/* in */ void) = 0;
    virtual IEcoLog1Layout* ECOCALLMETHOD get_Layout(/* in */ void) = 0;
    virtual void ECOCALLMETHOD set_Layout(/* in */ IEcoLog1Layout* pILayout) = 0;
    virtual int16_t ECOCALLMETHOD Write(/* in */ uint16_t level, /* in */ char_t* data, /* in */ uint32_t size) = 0;

    /* IEcoLog1FileAffiliate */
    virtual char_t* ECOCALLMETHOD get_FileName(/* in */ void) = 0;
    virtual void ECOCALLMETHOD set_FileName( /* in */ char_t* name) = 0;

};

#endif /* __I_ECO_LOG_1_FILE_AFFILIATE_HPP__ */

