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

#ifndef __I_ECO_STRING_C89_HPP__
#define __I_ECO_STRING_C89_HPP__

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

interface IEcoStringC89 : public IEcoUnknown {
public:
    /* IEcoStringC89 */
    virtual void* ECOCALLMETHOD memcpy(/* in */ void *s1, /* in */ const void *s2, /* in */ size_t n) = 0;
    virtual void* ECOCALLMETHOD memmove(/* in */ void *s1, /* in */ const void *s2, /* in */ size_t n) = 0;
    virtual char* ECOCALLMETHOD strcpy(/* in */ char *s1, /* in */ const char *s2) = 0;
    virtual char* ECOCALLMETHOD strncpy(/* in */ char *s1, /* in */ const char *s2, /* in */ size_t n) = 0;
    virtual char* ECOCALLMETHOD strcat(/* in */ char *s1, /* in */ const char *s2) = 0;
    virtual char* ECOCALLMETHOD strncat(/* in */ char *s1, /* in */ const char *s2, /* in */ size_t n) = 0;
    virtual int ECOCALLMETHOD memcmp(/* in */ const void *s1, /* in */ const void *s2, /* in */ size_t n) = 0;
    virtual int ECOCALLMETHOD strcmp(/* in */ const char *s1, /* in */ const char *s2) = 0;
    virtual int ECOCALLMETHOD strcoll(/* in */ const char *s1, /* in */ const char *s2) = 0;
    virtual int ECOCALLMETHOD strncmp(/* in */ const char *s1, /* in */ const char *s2, /* in */ size_t n) = 0;
    virtual size_t ECOCALLMETHOD strxfrm(/* in */ char *s1, /* in */ const char *s2, /* in */ size_t n) = 0;
    virtual void* ECOCALLMETHOD memchr(/* in */ const void *s, /* in */ int c, /* in */ size_t n) = 0;
    virtual char* ECOCALLMETHOD strchr(/* in */ const char *s, /* in */ int c) = 0;
    virtual size_t ECOCALLMETHOD strcspn(/* in */ const char *s1, /* in */ const char *s2) = 0;
    virtual char* ECOCALLMETHOD strpbrk(/* in */ const char *s1, /* in */ const char *s2) = 0;
    virtual char* ECOCALLMETHOD strrchr(/* in */ const char *s, /* in */ int c) = 0;
    virtual size_t ECOCALLMETHOD strspn(/* in */ const char *s1, /* in */ const char *s2) = 0;
    virtual char* ECOCALLMETHOD strstr(/* in */ const char *s1, /* in */ const char *s2) = 0;
    virtual char* ECOCALLMETHOD strtok(/* in */ char *s1, /* in */ const char *s2) = 0;
    virtual void* ECOCALLMETHOD memset(/* in */ void *s, /* in */ int c, /* in */ size_t n) = 0;
    virtual char* ECOCALLMETHOD strerror(/* in */ int errnum) = 0;
    virtual size_t ECOCALLMETHOD strlen(/* in */ const char *s) = 0;

};

#endif /* __I_ECO_STRING_C89_HPP__ */
