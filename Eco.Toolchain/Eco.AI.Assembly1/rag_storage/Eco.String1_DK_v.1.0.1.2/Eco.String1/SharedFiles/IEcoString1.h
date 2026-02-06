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

#ifndef __I_ECO_STRING_1_H__
#define __I_ECO_STRING_1_H__

#include "IEcoBase1.h"

#define ECO_STRING_1_TRIM_ALL   0
#define ECO_STRING_1_TRIM_BOTH  1
#define ECO_STRING_1_TRIM_START 2
#define ECO_STRING_1_TRIM_END   3

/* IEcoString1 IID = {488E33AE-7F84-4B83-A4F9-A8723847C3FD} */
#ifndef __IID_IEcoString1
static const UGUID IID_IEcoString1 = { 0x01, 0x10, {0x48, 0x8e, 0x33, 0xae, 0x7f, 0x84, 0x4b, 0x83, 0xa4, 0xf9, 0xa8, 0x72, 0x38, 0x47, 0xc3, 0xfd} };
#endif /* __IID_IEcoString1 */

typedef struct IEcoString1* IEcoString1Ptr_t;

typedef struct IEcoString1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface )(/* in */ IEcoString1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t *ppv);
    uint32_t (ECOCALLMETHOD *AddRef )(/* in */ IEcoString1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release )(/* in */ IEcoString1Ptr_t me);

    /* IEcoString1 */
    char_t* (ECOCALLMETHOD *Clone)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz);
    int16_t (ECOCALLMETHOD *Compare)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz1, /* in */ char_t *psz2);
    int16_t (ECOCALLMETHOD *CompareCaseInsensitive)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz1, /* in */ char_t *psz2);
    uint32_t (ECOCALLMETHOD *RetrieveSize)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz);
    char_t* (ECOCALLMETHOD *SearchSubstring)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz, /* in */ char_t *pszSearch);
    char_t* (ECOCALLMETHOD *SearchFirstCharacter)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz, /* in */ uint16_t Character);
    char_t* (ECOCALLMETHOD *SearchLastCharacter)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz, /* in */ uint16_t Character);
    char_t* (ECOCALLMETHOD *SearchAnyCharacter)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz, /* in */ char_t *pszCharacter);
    char_t* (ECOCALLMETHOD *Append)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz1, /* in */ char_t *psz2);
    char_t* (ECOCALLMETHOD *Assign)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz1, /* in */ char_t *psz2);
    int32_t (ECOCALLMETHOD *ConvertToLong)(/* in */ IEcoString1Ptr_t me, /* in */ const char_t *psz, /* in */ char_t **endptr, /* in */ int16_t base);
    int32_t (ECOCALLMETHOD *ConvertDecToInt)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz);
    int32_t (ECOCALLMETHOD *ConvertHexToInt)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz);
    int32_t (ECOCALLMETHOD *ConvertBinToInt)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz);
    int32_t (ECOCALLMETHOD *ConvertOctToInt)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz);
    char_t* (ECOCALLMETHOD *ConvertLongToString)(/* in */ IEcoString1Ptr_t me, /* in */ int32_t value, /* in */ int16_t base, /* in */ bool_t alt);
    char_t* (ECOCALLMETHOD *ConvertIntToString)(/* in */ IEcoString1Ptr_t me, /* in */ int32_t value);
    char_t* (ECOCALLMETHOD *ConvertIntToFormatString)(/* in */ IEcoString1Ptr_t me, /* in */ int32_t value, /* in */ char_t *format);
    bool_t (ECOCALLMETHOD *IsAlpha)(/* in */ IEcoString1Ptr_t me, /* in */ uint16_t Character);
    bool_t (ECOCALLMETHOD *IsDigit)(/* in */ IEcoString1Ptr_t me, /* in */ uint16_t Character);
    bool_t (ECOCALLMETHOD *IsHexDigit)(/* in */ IEcoString1Ptr_t me, /* in */ uint16_t Character);
    bool_t (ECOCALLMETHOD *IsAlphanumeric)(/* in */ IEcoString1Ptr_t me, /* in */ uint16_t Character);
    bool_t (ECOCALLMETHOD *IsPunctuation)(/* in */ IEcoString1Ptr_t me, /* in */ uint16_t Character);
    bool_t (ECOCALLMETHOD *IsLower)(/* in */ IEcoString1Ptr_t me, /* in */ uint16_t Character);
    bool_t (ECOCALLMETHOD *IsUpper)(/* in */ IEcoString1Ptr_t me, /* in */ uint16_t Character);
    bool_t (ECOCALLMETHOD *IsSpace)(/* in */ IEcoString1Ptr_t me, /* in */ uint16_t Character);
    uint16_t (ECOCALLMETHOD *ToLower)(/* in */ IEcoString1Ptr_t me, /* in */ uint16_t Character);
    uint16_t (ECOCALLMETHOD *ToUpper)(/* in */ IEcoString1Ptr_t me, /* in */ uint16_t Character);
    char_t* (ECOCALLMETHOD *ToFormatString)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *format, /* in */ ...);
    char_t* (ECOCALLMETHOD *VarArgListToFormatString)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *format, /* in */ va_list arg);
    char_t* (ECOCALLMETHOD *ToLowerString)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz);
    char_t* (ECOCALLMETHOD *ToUpperString)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz);
    void (ECOCALLMETHOD *Free)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz);
    char_t* (ECOCALLMETHOD *Replace)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *pszString, /* in */ char_t *pszSubString, /* in */ char_t *pszReplacement);
    char_t* (ECOCALLMETHOD *Substring)(/* in */ IEcoString1Ptr_t me, /* in */ char_t *psz, /* in */ uint32_t start, /* in */ uint32_t length);
    char_t* (ECOCALLMETHOD *Repeate)(/* in */ IEcoString1Ptr_t me, /* in */ char_t* psz, /* in */ uint32_t count);
    char_t* (ECOCALLMETHOD *Trim)(/* in */ IEcoString1Ptr_t me, /* in */ char_t* psz, /* in */ char_t trimChars[], /* in */ uint32_t length, /* in */ uint8_t flag);
    int16_t (ECOCALLMETHOD *Split)(/* in */ IEcoString1Ptr_t me, /* in */ char_t* psz, /* in */ char_t separators[], /* in */ uint32_t lengthSeparators, /* out */ char_t** pszArray[], /* out */ uint32_t* lengthArray);
    char_t* (ECOCALLMETHOD *Join)(/* in */ IEcoString1Ptr_t me, /* in */ char_t* separator, /* in */ char_t* pszArray[], /* in */ uint32_t lengthArray);


} IEcoString1VTbl, *IEcoString1VTblPtr;

interface IEcoString1 {
    struct IEcoString1VTbl *pVTbl;
} IEcoString1;

#endif /* __I_ECO_STRING_1_H__ */
