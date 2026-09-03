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

#ifndef __I_ECO_LOG_1_HPP__
#define __I_ECO_LOG_1_HPP__

#include "IEcoBase1.hpp"

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
static const UGUID IID_IEcoLog1Layout = {0x01, 0x10, 0x75, 0x96, 0xA0, 0x90, 0x38, 0x47, 0x44, 0xEA, 0xBE, 0xDB, 0xEA, 0x4F, 0x4E, 0xEE, 0x5D, 0xA1};
#endif /* __IID_IEcoLog1Layout */

interface IEcoLog1Layout : public IEcoUnknown {

    /* IEcoLog1Layout */
    virtual char_t* ECOCALLMETHOD get_Name(/* in */ void) = 0;
    virtual char_t* ECOCALLMETHOD Format(/* in */ uint16_t level, /* in */ char_t* data, /* in */ uint32_t size) = 0;

};

/* IEcoLog1Affiliate IID = {6A744539-3376-4D4B-BF3C-1FABE5BBC18F} */
#ifndef __IID_IEcoLog1Affiliate
static const UGUID IID_IEcoLog1Affiliate = {0x01, 0x10, 0x6A, 0x74, 0x45, 0x39, 0x33, 0x76, 0x4D, 0x4B, 0xBF, 0x3C, 0x1F, 0xAB, 0xE5, 0xBB, 0xC1, 0x8F};
#endif /* __IID_IEcoLog1Affiliate */

interface IEcoLog1Affiliate : public IEcoUnknown {

    /* IEcoLog1Affiliate */
    virtual char_t* ECOCALLMETHOD get_Name(/* in */void) = 0;
    virtual IEcoLog1Layout* ECOCALLMETHOD get_Layout(/* in */ void) = 0;
    virtual void ECOCALLMETHOD set_Layout(/* in */ IEcoLog1Layout* pILayout) = 0;
    virtual int16_t ECOCALLMETHOD Write(/* in */ uint16_t level, /* in */ char_t* data, /* in */ uint32_t size) = 0;

};

/* IEcoLog1 IID = {F3B19793-BD14-4E9F-B7EA-64EDF4B6453F} */
#ifndef __IID_IEcoLog1
static const UGUID IID_IEcoLog1 = {0x01, 0x10, 0xF3, 0xB1, 0x97, 0x93, 0xBD, 0x14, 0x4E, 0x9F, 0xB7, 0xEA, 0x64, 0xED, 0xF4, 0xB6, 0x45, 0x3F};
#endif /* __IID_IEcoLog1 */

interface IEcoLog1 : public IEcoUnknown {

    /* IEcoLog1 */
    virtual int16_t ECOCALLMETHOD AddAffiliate(/* in */ IEcoLog1Affiliate* pIAffiliate) = 0;
    virtual void ECOCALLMETHOD set_LevelMask(/* in */ uint16_t mask) = 0;
    virtual uint16_t ECOCALLMETHOD get_LevelMask(/* in */ void) = 0;
    virtual void ECOCALLMETHOD Debug(/* in */ char_t* message) = 0;
    virtual void ECOCALLMETHOD Info(/* in */ char_t* message) = 0;
    virtual void ECOCALLMETHOD Warn(/* in */ char_t* message) = 0;
    virtual void ECOCALLMETHOD Error(/* in */ char_t* message) = 0;
    virtual void ECOCALLMETHOD Fatal(/* in */ char_t* message) = 0;
    virtual void ECOCALLMETHOD DebugFormat(/* in */ char_t* format, ...) = 0;
    virtual void ECOCALLMETHOD InfoFormat(/* in */ char_t* format, ...) = 0;
    virtual void ECOCALLMETHOD WarnFormat(/* in */ char_t* format, ...);
    virtual void ECOCALLMETHOD ErrorFormat(/* in */ char_t* format, ...) = 0;
    virtual void ECOCALLMETHOD FatalFormat(/* in */ char_t* format, ...) = 0;
    virtual void ECOCALLMETHOD HexDump(/* in */ char_t* data, /* in */ uint32_t size) = 0;
    virtual void ECOCALLMETHOD BinDump(/* in */ uint32_t data, /* in */ byte_t bits) = 0;
};

#endif /* __I_ECO_LOG_1_HPP__ */
