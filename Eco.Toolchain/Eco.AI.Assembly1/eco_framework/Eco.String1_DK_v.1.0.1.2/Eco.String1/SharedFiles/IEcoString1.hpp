/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoString1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoString1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_STRING_1_HPP__
#define __I_ECO_STRING_1_HPP__

#include "IEcoBase1.hpp"

#define ECO_STRING_1_TRIM_ALL   0
#define ECO_STRING_1_TRIM_BOTH  1
#define ECO_STRING_1_TRIM_START 2
#define ECO_STRING_1_TRIM_END   3

/* IEcoString1 IID = {488E33AE-7F84-4B83-A4F9-A8723847C3FD} */
#ifndef __IID_IEcoString1
static const UGUID IID_IEcoString1 = { 0x01, 0x10, {0x48, 0x8e, 0x33, 0xae, 0x7f, 0x84, 0x4b, 0x83, 0xa4, 0xf9, 0xa8, 0x72, 0x38, 0x47, 0xc3, 0xfd} };
#endif /* __IID_IEcoString1 */

interface IEcoString1 : public IEcoUnknown {
public:
    /* IEcoString1 */
    virtual char_t* ECOCALLMETHOD Clone(/* in */ char_t *psz) = 0;
    virtual int16_t ECOCALLMETHOD Compare(/* in */ char_t *psz1, /* in */ char_t *psz2) = 0;
    virtual int16_t ECOCALLMETHOD CompareCaseInsensitive(/* in */ char_t *psz1, /* in */ char_t *psz2) = 0;
    virtual uint32_t ECOCALLMETHOD RetrieveSize(/* in */ char_t *psz) = 0;
    virtual char_t* ECOCALLMETHOD SearchSubstring(/* in */ char_t *psz, /* in */ char_t *pszSearch) = 0;
    virtual char_t* ECOCALLMETHOD SearchFirstCharacter(/* in */ char_t *psz, /* in */ uint16_t Character) = 0;
    virtual char_t* ECOCALLMETHOD SearchLastCharacter(/* in */ char_t *psz, /* in */ uint16_t Character) = 0;
    virtual char_t* ECOCALLMETHOD SearchAnyCharacter(/* in */ char_t *psz, /* in */ char_t *pszCharacter) = 0;
    virtual char_t* ECOCALLMETHOD Append(/* in */ char_t *psz1, /* in */ char_t *psz2) = 0;
    virtual char_t* ECOCALLMETHOD Assign(/* in */ char_t *psz1, /* in */ char_t *psz2) = 0;
    virtual int32_t ECOCALLMETHOD ConvertToLong(/* in */ const char_t *psz, /* in */ char_t **endptr, /* in */ int16_t base) = 0;
    virtual int32_t ECOCALLMETHOD ConvertDecToInt(/* in */ char_t *psz) = 0;
    virtual int32_t ECOCALLMETHOD ConvertHexToInt(/* in */ char_t *psz) = 0;
    virtual int32_t ECOCALLMETHOD ConvertBinToInt(/* in */ char_t *psz) = 0;
    virtual int32_t ECOCALLMETHOD ConvertOctToInt(/* in */ char_t *psz) = 0;
    virtual char_t* ECOCALLMETHOD ConvertLongToString(/* in */ int32_t value, /* in */ int16_t base, /* in */ bool_t alt) = 0;
    virtual char_t* ECOCALLMETHOD ConvertIntToString(/* in */ int32_t value) = 0;
    virtual char_t* ECOCALLMETHOD ConvertIntToFormatString(/* in */ int32_t value, /* in */ char_t *format) = 0;
    virtual bool_t ECOCALLMETHOD IsAlpha(/* in */ uint16_t Character) = 0;
    virtual bool_t ECOCALLMETHOD IsDigit(/* in */ uint16_t Character) = 0;
    virtual bool_t ECOCALLMETHOD IsHexDigit(/* in */ uint16_t Character) = 0;
    virtual bool_t ECOCALLMETHOD IsAlphanumeric(/* in */ uint16_t Character) = 0;
    virtual bool_t ECOCALLMETHOD IsPunctuation(/* in */ uint16_t Character) = 0;
    virtual bool_t ECOCALLMETHOD IsLower(/* in */ uint16_t Character) = 0;
    virtual bool_t ECOCALLMETHOD IsUpper(/* in */ uint16_t Character) = 0;
    virtual bool_t ECOCALLMETHOD IsSpace(/* in */ uint16_t Character) = 0;
    virtual uint16_t ECOCALLMETHOD ToLower(/* in */ uint16_t Character) = 0;
    virtual uint16_t ECOCALLMETHOD ToUpper(/* in */ uint16_t Character) = 0;
    virtual char_t* ECOCALLMETHOD ToFormatString(/* in */ char_t *format, /* in */ ...) = 0;
    virtual char_t* ECOCALLMETHOD VarArgListToFormatString(/* in */ char_t *format, /* in */ va_list arg) = 0;
    virtual char_t* ECOCALLMETHOD ToLowerString(/* in */ char_t *psz) = 0;
    virtual char_t* ECOCALLMETHOD ToUpperString(/* in */ char_t *psz) = 0;
    virtual void ECOCALLMETHOD Free(/* in */ char_t *psz) = 0;
    virtual char_t* ECOCALLMETHOD Replace(/* in */ char_t *pszString, /* in */ char_t *pszSubString, /* in */ char_t *pszReplacement) = 0;
    virtual char_t* ECOCALLMETHOD Substring(/* in */ char_t *psz, /* in */ uint32_t start, /* in */ uint32_t length) = 0;
    virtual char_t* ECOCALLMETHOD Repeate(/* in */ char_t* psz, /* in */ uint32_t count) = 0;
    virtual char_t* ECOCALLMETHOD Trim(/* in */ char_t* psz, /* in */ char_t trimChars[], /* in */ uint32_t length, /* in */ uint8_t flag) = 0;
    virtual int16_t ECOCALLMETHOD Split(/* in */ char_t* psz, /* in */ char_t separators[], /* in */ uint32_t lengthSeparators, /* out */ char_t** pszArray[], /* out */ uint32_t* lengthArray) = 0;
    virtual char_t* ECOCALLMETHOD Join(/* in */ char_t* separator, /* in */ char_t* pszArray[], /* in */ uint32_t lengthArray) = 0;

};

#endif /* __I_ECO_STRING_1_HPP__ */
