/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoStdIOC89
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoStdIOC89
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

#ifndef __I_ECO_STD_IO_C89_HPP__
#define __I_ECO_STD_IO_C89_HPP__

#include "IEcoBase1.hpp"

#ifdef ECO_OS
#ifndef __ECO_STDIO_H__

#define _IOFBF      0x0
#define _IOLBF      0x40
#define _IONBF      0x04

#define BUFSIZ  512
#define EOF (-1)

#ifndef ECO_FILE_DEFINED
struct _iobuf {
    char *_ptr;
    int   _cnt;
    char *_base;
    char  _flag;
    char  _file;
};
typedef struct _iobuf FILE;
#define ECO_FILE_DEFINED
#endif 

#define FILENAME_MAX 128
#define FOPEN_MAX 18

#ifndef ECO_FPOS_T_DEFINED
typedef long fpos_t;
#define ECO_FPOS_T_DEFINED
#endif 

#define  L_tmpnam sizeof("\\")+8

#ifndef NULL
#define NULL ((void *)0)
#endif

#define SEEK_CUR 1
#define SEEK_END 2
#define SEEK_SET 0

#ifndef ECO_SIZE_T_DEFINED
typedef unsigned int size_t;
#define ECO_SIZE_T_DEFINED
#endif 

#ifndef _VA_LIST_DEFINED
typedef char *va_list;
#define _VA_LIST_DEFINED
#endif 

#define stdin  (&_iob[0])
#define stdout (&_iob[1])
#define stderr (&_iob[2])

#define TMP_MAX 32767

#endif
#endif

/* IEcoStdIOC89 IID = {00000000-0000-0000-0000-890000008101} */
#ifndef __IID_IEcoStdIOC89
static const UGUID IID_IEcoStdIOC89 = {0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x89, 0x00, 0x00, 0x00, 0x81, 0x01}};
#endif /* __IID_IEcoStdIOC89 */

interface IEcoStdIOC89 : public IEcoUnknown {
public:
    /* IEcoStdIOC89 */
    virtual int ECOCALLMETHOD *remove(/* in */ const char *filename) = 0;
    virtual int ECOCALLMETHOD rename(/* in */ const char *old, /* in */ const char *new) = 0;
    virtual FILE *ECOCALLMETHOD tmpfile(/* in*/ void) = 0;
    virtual char *ECOCALLMETHOD tmpnam(/* in */ char *s) = 0;
    virtual int ECOCALLMETHOD fclose(/* in */ FILE *stream) = 0;
    virtual int ECOCALLMETHOD fflush(/* in */ FILE *stream) = 0;
    virtual FILE *ECOCALLMETHOD fopen(/* in */ const char *filename, /* in */ const char *mode) = 0;
    virtual FILE *ECOCALLMETHOD freopen(/* in */ const char *filename, /* in */ const char *mode, /* in */ FILE *stream) = 0;
    virtual void ECOCALLMETHOD setbuf(/* in */ FILE *stream, /* in */ char *buf) = 0;
    virtual int ECOCALLMETHOD setvbuf(/* in */ FILE *stream, /* in */ char *buf, /* in */ int mode, /* in */ size_t size) = 0;
    virtual int ECOCALLMETHOD fprintf(/* in */ FILE *stream, /* in */ const char *format, ...) = 0;
    virtual int ECOCALLMETHOD fscanf(/* in */ FILE *stream, /* in */ const char *format, ...) = 0;
    virtual int ECOCALLMETHOD printf(/* in */ const char *format, ...) = 0;
    virtual int ECOCALLMETHOD scanf(/* in */ const char *format, ...) = 0;
    virtual int ECOCALLMETHOD sprintf(/* in */ char *s, /* in */ const char *format, ...) = 0;
    virtual int ECOCALLMETHOD sscanf(/* in */ const char *s, /* in */ const char *format, ...) = 0;
    virtual int ECOCALLMETHOD vfprintf(/* in */ FILE *stream, /* in */ const char *format, /* in */ va_list arg) = 0;
    virtual int ECOCALLMETHOD vprintf(/* in */ const char *format, /* in */ va_list arg) = 0;
    virtual int ECOCALLMETHOD vsprintf(/* in */ char *s, /* in */ const char *format, /* in */ va_list arg) = 0;
    virtual int ECOCALLMETHOD fgetc(/* in */ FILE *stream) = 0;
    virtual char *ECOCALLMETHOD fgets(/* in */ char *s, /* in */ int n, /* in */ FILE *stream) = 0;
    virtual int ECOCALLMETHOD fputc(/* in */ int c, /* in */ FILE *stream) = 0;
    virtual int ECOCALLMETHOD fputs(/* in */ const char *s, /* in */ FILE *stream) = 0;
    virtual int ECOCALLMETHOD getc(/* in */ FILE *stream) = 0;
    virtual int ECOCALLMETHOD getchar(/* in*/ void) = 0;
    virtual char *ECOCALLMETHOD gets(/* in */ char *s) = 0;
    virtual int ECOCALLMETHOD putc(/* in */ int c, /* in */ FILE *stream) = 0;
    virtual int ECOCALLMETHOD putchar(/* in */ int c) = 0;
    virtual int ECOCALLMETHOD puts(/* in */ const char *s) = 0;
    virtual int ECOCALLMETHOD ungetc(/* in */ int c, /* in */ FILE *stream) = 0;
    virtual size_t ECOCALLMETHOD fread(/* in */ void *ptr, /* in */ size_t size, /* in */ size_t nmemb, /* in */ FILE *stream) = 0;
    virtual size_t ECOCALLMETHOD fwrite(/* in */ const void *ptr, /* in */ size_t size, /* in */ size_t nmemb, /* in */ FILE *stream) = 0;
    virtual int ECOCALLMETHOD fgetpos(/* in */ FILE *stream, /* in */ fpos_t *pos) = 0;
    virtual int ECOCALLMETHOD fseek(/* in */ FILE *stream, /* in */ long int offset, /* in */ int whence) = 0;
    virtual int ECOCALLMETHOD fsetpos(/* in */ FILE *stream, /* in */ const fpos_t *pos) = 0;
    virtual long int ECOCALLMETHOD ftell(/* in */ FILE *stream) = 0;
    virtual void ECOCALLMETHOD rewind(/* in */ FILE *stream) = 0;
    virtual void ECOCALLMETHOD clearerr(/* in */ FILE *stream) = 0;
    virtual int ECOCALLMETHOD feof(/* in */ FILE *stream) = 0;
    virtual int ECOCALLMETHOD ferror(/* in */ FILE *stream) = 0;
    virtual void ECOCALLMETHOD perror(/* in */ const char *s) = 0;

};

#endif /* __I_ECO_STD_IO_C89_HPP__ */
