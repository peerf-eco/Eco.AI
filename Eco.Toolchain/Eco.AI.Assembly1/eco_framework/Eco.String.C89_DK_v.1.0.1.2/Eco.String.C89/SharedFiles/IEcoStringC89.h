/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoStringC89
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoStringC89
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

#ifndef __I_ECO_STRING_C89_H__
#define __I_ECO_STRING_C89_H__

#include "IEcoBase1.h"

#ifdef ECO_OS
#ifndef __ECO_STRING_H__

#ifndef NULL
#define NULL ((void *)0)
#endif

#ifndef ECO_SIZE_T_DEFINED
typedef unsigned int size_t;
#define ECO_SIZE_T_DEFINED
#endif

#endif
#endif

/* IEcoStringC89 IID = {00000000-0000-0000-0000-890000001101} */
#ifndef __IID_IEcoStringC89
static const UGUID IID_IEcoStringC89 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x89, 0x00, 0x00, 0x00, 0x11, 0x01}};
#endif /* __IID_IEcoStringC89 */

typedef struct IEcoStringC89* IEcoStringC89Ptr_t;

typedef struct IEcoStringC89VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoStringC89Ptr_t me, /* in */ const UGUID* riid, /* out */ void **ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoStringC89Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoStringC89Ptr_t me);

    /* IEcoStringC89 */
    void* (ECOCALLMETHOD *memcpy)(/* in */ IEcoStringC89Ptr_t me, /* in */ void *s1, /* in */ const void *s2, /* in */ size_t n);
    void* (ECOCALLMETHOD *memmove)(/* in */ IEcoStringC89Ptr_t me, /* in */ void *s1, /* in */ const void *s2, /* in */ size_t n);
    char* (ECOCALLMETHOD *strcpy)(/* in */ IEcoStringC89Ptr_t me, /* in */ char *s1, /* in */ const char *s2);
    char* (ECOCALLMETHOD *strncpy)(/* in */ IEcoStringC89Ptr_t me, /* in */ char *s1, /* in */ const char *s2, /* in */ size_t n);
    char* (ECOCALLMETHOD *strcat)(/* in */ IEcoStringC89Ptr_t me, /* in */ char *s1, /* in */ const char *s2);
    char* (ECOCALLMETHOD *strncat)(/* in */ IEcoStringC89Ptr_t me, /* in */ char *s1, /* in */ const char *s2, /* in */ size_t n);
    int (ECOCALLMETHOD *memcmp)(/* in */ IEcoStringC89Ptr_t me, /* in */ const void *s1, /* in */ const void *s2, /* in */ size_t n);
    int (ECOCALLMETHOD *strcmp)(/* in */ IEcoStringC89Ptr_t me, /* in */ const char *s1, /* in */ const char *s2);
    int (ECOCALLMETHOD *strcoll)(/* in */ IEcoStringC89Ptr_t me, /* in */ const char *s1, /* in */ const char *s2);
    int (ECOCALLMETHOD *strncmp)(/* in */ IEcoStringC89Ptr_t me, /* in */ const char *s1, /* in */ const char *s2, /* in */ size_t n);
    size_t (ECOCALLMETHOD *strxfrm)(/* in */ IEcoStringC89Ptr_t me, /* in */ char *s1, /* in */ const char *s2, /* in */ size_t n);
    void* (ECOCALLMETHOD *memchr)(/* in */ IEcoStringC89Ptr_t me, /* in */ const void *s, /* in */ int c, /* in */ size_t n);
    char* (ECOCALLMETHOD *strchr)(/* in */ IEcoStringC89Ptr_t me, /* in */ const char *s, /* in */ int c);
    size_t (ECOCALLMETHOD *strcspn)(/* in */ IEcoStringC89Ptr_t me, /* in */ const char *s1, /* in */ const char *s2);
    char* (ECOCALLMETHOD *strpbrk)(/* in */ IEcoStringC89Ptr_t me, /* in */ const char *s1, /* in */ const char *s2);
    char* (ECOCALLMETHOD *strrchr)(/* in */ IEcoStringC89Ptr_t me, /* in */ const char *s, /* in */ int c);
    size_t (ECOCALLMETHOD *strspn)(/* in */ IEcoStringC89Ptr_t me, /* in */ const char *s1, /* in */ const char *s2);
    char* (ECOCALLMETHOD *strstr)(/* in */ IEcoStringC89Ptr_t me, /* in */ const char *s1, /* in */ const char *s2);
    char* (ECOCALLMETHOD *strtok)(/* in */ IEcoStringC89Ptr_t me, /* in */ char *s1, /* in */ const char *s2);
    void* (ECOCALLMETHOD *memset)(/* in */ IEcoStringC89Ptr_t me, /* in */ void *s, /* in */ int c, /* in */ size_t n);
    char* (ECOCALLMETHOD *strerror)(/* in */ IEcoStringC89Ptr_t me, /* in */ int errnum);
    size_t (ECOCALLMETHOD *strlen)(/* in */ IEcoStringC89Ptr_t me, /* in */ const char *s);

} IEcoStringC89VTbl, *IEcoStringC89VTblPtr;

interface IEcoStringC89 {
    struct IEcoStringC89VTbl *pVTbl;
} IEcoStringC89;


#endif /* __I_ECO_STRING_C89_H__ */
