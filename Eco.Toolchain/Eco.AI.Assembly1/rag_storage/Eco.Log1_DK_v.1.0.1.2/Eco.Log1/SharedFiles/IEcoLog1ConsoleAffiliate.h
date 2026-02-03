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

#ifndef __I_ECO_LOG_1_CONSOLE_AFFILIATE_H__
#define __I_ECO_LOG_1_CONSOLE_AFFILIATE_H__

#include "IEcoBase1.h"
#include "IEcoLog1.h"

/* IEcoLog1ConsoleAffiliate IID = {FECB29A2-3D60-4501-9F83-47C4752CFA3A} */
#ifndef __IID_IEcoLog1ConsoleAffiliate
static const UGUID IID_IEcoLog1ConsoleAffiliate = {0x01, 0x10, {0xFE, 0xCB, 0x29, 0xA2, 0x3D, 0x60, 0x45, 0x01, 0x9F, 0x83, 0x47, 0xC4, 0x75, 0x2C, 0xFA, 0x3A}};
#endif /* __IID_IEcoLog1ConsoleAffiliate */

typedef struct IEcoLog1ConsoleAffiliate* IEcoLog1ConsoleAffiliatePtr_t;

typedef struct IEcoLog1ConsoleAffiliateVTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface )(/* in */ IEcoLog1ConsoleAffiliatePtr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef )(/* in */ IEcoLog1ConsoleAffiliatePtr_t me);
    uint32_t (ECOCALLMETHOD *Release )(/* in */ IEcoLog1ConsoleAffiliatePtr_t me);

    /* IEcoLog1Affiliate */
    char_t* (ECOCALLMETHOD *get_Name)(/* in */ IEcoLog1ConsoleAffiliatePtr_t me);
    IEcoLog1Layout* (ECOCALLMETHOD *get_Layout)(/* in */ IEcoLog1ConsoleAffiliatePtr_t me);
    void (ECOCALLMETHOD *set_Layout)(/* in */ IEcoLog1ConsoleAffiliatePtr_t me, /* in */ IEcoLog1Layout* pILayout);
    int16_t (ECOCALLMETHOD *Write)(/* in */ IEcoLog1ConsoleAffiliatePtr_t me, /* in */ uint16_t level, /* in */ char_t* data, /* in */ uint32_t size);

    /* IEcoLog1ConsoleAffiliate */
    char_t* (ECOCALLMETHOD *get_TargetOutput)(/* in */ IEcoLog1ConsoleAffiliatePtr_t me);
    void (ECOCALLMETHOD *set_TargetOutput)(/* in */ IEcoLog1ConsoleAffiliatePtr_t me, /* in */ char_t* name);

} IEcoLog1ConsoleAffiliateVTbl, *IEcoLog1ConsoleAffiliateVTblPtr;

interface IEcoLog1ConsoleAffiliate {
    struct IEcoLog1ConsoleAffiliateVTbl *pVTbl;
} IEcoLog1ConsoleAffiliate;

#endif /* __I_ECO_LOG_1_CONSOLE_AFFILIATE_H__ */

