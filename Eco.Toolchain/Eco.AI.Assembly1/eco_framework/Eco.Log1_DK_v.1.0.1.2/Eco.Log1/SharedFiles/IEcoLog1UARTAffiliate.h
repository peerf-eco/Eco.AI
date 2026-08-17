/*
 * <кодировка символов>
 *   Cyrillic (Windows) - Codepage 1251
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoLog1UARTAffiliate
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoLog1UARTAffiliate
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

#ifndef __I_ECO_LOG_1_UART_AFFILIATE_H__
#define __I_ECO_LOG_1_UART_AFFILIATE_H__

#include "IEcoBase1.h"
#include "IEcoLog1.h"

/* IEcoLog1UARTAffiliate IID = {22B0B071-478D-461A-9F5B-5F40D4D79B7A} */
#ifndef __IID_IEcoLog1UARTAffiliate
static const UGUID IID_IEcoLog1UARTAffiliate = {0x01, 0x10, {0x22, 0xB0, 0xB0, 0x71, 0x47, 0x8D, 0x46, 0x1A, 0x9F, 0x5B, 0x5F, 0x40, 0xD4, 0xD7, 0x9B, 0x7A} };
#endif /* __IID_IEcoLog1UARTAffiliate */

typedef struct IEcoLog1UARTAffiliate* IEcoLog1UARTAffiliatePtr_t;

typedef struct IEcoLog1UARTAffiliateVTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface )(/* in */ IEcoLog1UARTAffiliatePtr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef )(/* in */ IEcoLog1UARTAffiliatePtr_t me);
    uint32_t (ECOCALLMETHOD *Release )(/* in */ IEcoLog1UARTAffiliatePtr_t me);

    /* IEcoLog1Affiliate */
    char_t* (ECOCALLMETHOD *get_Name)(/* in */ IEcoLog1UARTAffiliatePtr_t me);
    IEcoLog1Layout* (ECOCALLMETHOD *get_Layout)(/* in */ IEcoLog1UARTAffiliatePtr_t me);
    void (ECOCALLMETHOD *set_Layout)(/* in */ IEcoLog1UARTAffiliatePtr_t me, /* in */ IEcoLog1Layout* pILayout);
    int16_t (ECOCALLMETHOD *Write)(/* in */ IEcoLog1UARTAffiliatePtr_t me, /* in */ uint16_t level, /* in */ char_t* data, /* in */ uint32_t size);

    /* IEcoLog1UARTAffiliate */
    char_t* (ECOCALLMETHOD *get_UARTName)(/* in */ IEcoLog1UARTAffiliatePtr_t me);
    void (ECOCALLMETHOD *set_UARTName)(/* in */ IEcoLog1UARTAffiliatePtr_t me, /* in */ char_t* name);

} IEcoLog1UARTAffiliateVTbl, *IEcoLog1UARTAffiliateVTblPtr;

interface IEcoLog1UARTAffiliate {
    struct IEcoLog1UARTAffiliateVTbl *pVTbl;
} IEcoLog1UARTAffiliate;

#endif /* __I_ECO_LOG_1_UART_AFFILIATE_H__ */

