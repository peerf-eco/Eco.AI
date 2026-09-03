/*
 * <кодировка символов>
 *   Cyrillic (Windows) - Codepage 1251
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoLog1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoLog1
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

#ifndef __I_ECO_LOG_1_H__
#define __I_ECO_LOG_1_H__

#include "IEcoBase1.h"

/* Log Level */
enum eEcoLog1Level {
    ECO_LOG_1_LEVEL_DEBUG = 1,
    ECO_LOG_1_LEVEL_INFO = 2,
    ECO_LOG_1_LEVEL_WARN = 4,
    ECO_LOG_1_LEVEL_ERROR = 8,
    ECO_LOG_1_LEVEL_FATAL = 16
};

/* IEcoLog1Layout IID = {7596A090-3847-44EA-BEDB-EA4F4EEE5DA1} */
#ifndef __IID_IEcoLog1Layout
static const UGUID IID_IEcoLog1Layout = {0x01, 0x10, {0x75, 0x96, 0xA0, 0x90, 0x38, 0x47, 0x44, 0xEA, 0xBE, 0xDB, 0xEA, 0x4F, 0x4E, 0xEE, 0x5D, 0xA1} };
#endif /* __IID_IEcoLog1Layout */

typedef struct IEcoLog1Layout* IEcoLog1LayoutPtr_t;

typedef struct IEcoLog1LayoutVTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface )(/* in */ IEcoLog1LayoutPtr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef )(/* in */ IEcoLog1LayoutPtr_t me);
    uint32_t (ECOCALLMETHOD *Release )(/* in */ IEcoLog1LayoutPtr_t me);

    /* IEcoLog1Layout */
    char_t* (ECOCALLMETHOD *get_Name)(/* in */ IEcoLog1LayoutPtr_t me);
    char_t* (ECOCALLMETHOD *Format)(/* in */ IEcoLog1LayoutPtr_t me, /* in */ uint16_t level, /* in */ char_t* data, /* in */ uint32_t size);

} IEcoLog1LayoutVTbl, *IEcoLog1LayoutVTblPtr;

interface IEcoLog1Layout {
    struct IEcoLog1LayoutVTbl *pVTbl;
} IEcoLog1Layout;

/* IEcoLog1Affiliate IID = {6A744539-3376-4D4B-BF3C-1FABE5BBC18F} */
#ifndef __IID_IEcoLog1Affiliate
static const UGUID IID_IEcoLog1Affiliate = {0x01, 0x10, {0x6A, 0x74, 0x45, 0x39, 0x33, 0x76, 0x4D, 0x4B, 0xBF, 0x3C, 0x1F, 0xAB, 0xE5, 0xBB, 0xC1, 0x8F} };
#endif /* __IID_IEcoLog1Affiliate */

typedef struct IEcoLog1Affiliate* IEcoLog1AffiliatePtr_t;

typedef struct IEcoLog1AffiliateVTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface )(/* in */ IEcoLog1AffiliatePtr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t*  ppv);
    uint32_t (ECOCALLMETHOD *AddRef )(/* in */ IEcoLog1AffiliatePtr_t me);
    uint32_t (ECOCALLMETHOD *Release )(/* in */ IEcoLog1AffiliatePtr_t me);

    /* IEcoLog1Affiliate */
    char_t* (ECOCALLMETHOD *get_Name)(/* in */ IEcoLog1AffiliatePtr_t me);
    IEcoLog1Layout* (ECOCALLMETHOD *get_Layout)(/* in */ IEcoLog1AffiliatePtr_t me);
    void (ECOCALLMETHOD *set_Layout)(/* in */ IEcoLog1AffiliatePtr_t me, /* in */ IEcoLog1Layout* pILayout);
    int16_t (ECOCALLMETHOD *Write)(/* in */ IEcoLog1AffiliatePtr_t me, /* in */ uint16_t level, /* in */ char_t* data, /* in */ uint32_t size);

} IEcoLog1AffiliateVTbl, *IEcoLog1AffiliateVTblPtr;

interface IEcoLog1Affiliate {
    struct IEcoLog1AffiliateVTbl *pVTbl;
} IEcoLog1Affiliate;

/* IEcoLog1 IID = {F3B19793-BD14-4E9F-B7EA-64EDF4B6453F} */
#ifndef __IID_IEcoLog1
static const UGUID IID_IEcoLog1 = {0x01, 0x10, {0xF3, 0xB1, 0x97, 0x93, 0xBD, 0x14, 0x4E, 0x9F, 0xB7, 0xEA, 0x64, 0xED, 0xF4, 0xB6, 0x45, 0x3F} };
#endif /* __IID_IEcoLog1 */

typedef struct IEcoLog1* IEcoLog1Ptr_t;

typedef struct IEcoLog1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoLog1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t*  ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoLog1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoLog1Ptr_t me);

    /* IEcoLog1 */
    int16_t (ECOCALLMETHOD *AddAffiliate)(/* in */ IEcoLog1Ptr_t me, /* in */ IEcoLog1Affiliate* pIAffiliate);
    void (ECOCALLMETHOD *set_LevelMask)(/* in */ IEcoLog1Ptr_t me, /* in */ uint16_t mask);
    uint16_t (ECOCALLMETHOD *get_LevelMask)(/* in */ IEcoLog1Ptr_t me);
    void (ECOCALLMETHOD *Debug)(/* in */ IEcoLog1Ptr_t me, /* in */ char_t* message);
    void (ECOCALLMETHOD *Info)(/* in */ IEcoLog1Ptr_t me, /* in */ char_t* message);
    void (ECOCALLMETHOD *Warn)(/* in */ IEcoLog1Ptr_t me, /* in */ char_t* message);
    void (ECOCALLMETHOD *Error)(/* in */ IEcoLog1Ptr_t me, /* in */ char_t* message);
    void (ECOCALLMETHOD *Fatal)(/* in */ IEcoLog1Ptr_t me, /* in */ char_t* message);
    void (ECOCALLMETHOD *DebugFormat)(/* in */ IEcoLog1Ptr_t me, /* in */ char_t* format, ...);
    void (ECOCALLMETHOD *InfoFormat)(/* in */ IEcoLog1Ptr_t me, /* in */ char_t* format, ...);
    void (ECOCALLMETHOD *WarnFormat)(/* in */ IEcoLog1Ptr_t me, /* in */ char_t* format, ...);
    void (ECOCALLMETHOD *ErrorFormat)(/* in */ IEcoLog1Ptr_t me, /* in */ char_t* format, ...);
    void (ECOCALLMETHOD *FatalFormat)(/* in */ IEcoLog1Ptr_t me, /* in */ char_t* format, ...);
    void (ECOCALLMETHOD *HexDump)(/* in */ IEcoLog1Ptr_t me, /* in */ char_t* data, /* in */ uint32_t size);
    void (ECOCALLMETHOD *BinDump)(/* in */ IEcoLog1Ptr_t me, /* in */ uint32_t data, /* in */ byte_t bits);
} IEcoLog1VTbl, *IEcoLog1VTblPtr;

interface IEcoLog1 {
    struct IEcoLog1VTbl *pVTbl;
} IEcoLog1;

#endif /* __I_ECO_LOG_1_H__ */
