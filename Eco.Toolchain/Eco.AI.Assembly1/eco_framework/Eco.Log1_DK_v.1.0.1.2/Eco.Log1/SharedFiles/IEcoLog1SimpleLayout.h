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

#ifndef __I_ECO_LOG_1_SIMPLE_LAYOUT_H__
#define __I_ECO_LOG_1_SIMPLE_LAYOUT_H__

#include "IEcoBase1.h"
#include "IEcoLog1.h"

/* IEcoLog1SimpleLayout IID = {9485C6A5-2CBF-4D46-B8B5-94F60740BEE3} */
#ifndef __IID_IEcoLog1SimpleLayout
static const UGUID IID_IEcoLog1SimpleLayout = {0x01, 0x10, {0x94, 0x85, 0xC6, 0xA5, 0x2C, 0xBF, 0x4D, 0x46, 0xB8, 0xB5, 0x94, 0xF6, 0x07, 0x40, 0xBE, 0xE3} };
#endif /* __IID_IEcoLog1SimpleLayout */

typedef struct IEcoLog1SimpleLayout* IEcoLog1SimpleLayoutPtr_t;

typedef struct IEcoLog1SimpleLayoutVTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface )(/* in */ IEcoLog1SimpleLayoutPtr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef )(/* in */ IEcoLog1SimpleLayoutPtr_t me);
    uint32_t (ECOCALLMETHOD *Release )(/* in */ IEcoLog1SimpleLayoutPtr_t me);

    /* IEcoLog1SimpleLayout */
    char_t* (ECOCALLMETHOD *get_Name)(/* in */ IEcoLog1SimpleLayoutPtr_t me);
    char_t* (ECOCALLMETHOD *Format)(/* in */ IEcoLog1SimpleLayoutPtr_t me, /* in */ uint16_t level, /* in */ char_t* data, /* in */ uint32_t size);

    /* IEcoLog1SimpleLayout */
    char_t* (ECOCALLMETHOD *get_Pattern)(/* in */ IEcoLog1SimpleLayoutPtr_t me);
    void (ECOCALLMETHOD *set_Pattern)(/* in */ IEcoLog1SimpleLayoutPtr_t me, /* in */ char_t* name);

} IEcoLog1SimpleLayoutVTbl, *IEcoLog1SimpleLayoutVTblPtr;

interface IEcoLog1SimpleLayout {
    struct IEcoLog1SimpleLayoutVTbl *pVTbl;
} IEcoLog1SimpleLayout;

#endif /* __I_ECO_LOG_1_SIMPLE_LAYOUT_H__ */

