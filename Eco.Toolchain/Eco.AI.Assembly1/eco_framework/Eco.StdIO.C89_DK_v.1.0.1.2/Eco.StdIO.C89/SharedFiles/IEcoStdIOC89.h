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

#ifndef __I_ECO_STD_IO_C89_H__
#define __I_ECO_STD_IO_C89_H__

#include "IEcoBase1.h"

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

typedef struct IEcoStdIOC89* IEcoStdIOC89Ptr_t;

typedef struct IEcoStdIOC89VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoStdIOC89Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoStdIOC89Ptr_t me);

    /* IEcoStdIOC89 */
    int (ECOCALLMETHOD *remove)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ const char *filename);
    int (ECOCALLMETHOD *rename)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ const char *old, /* in */ const char *new);
    FILE *(ECOCALLMETHOD *tmpfile)(/* in */ IEcoStdIOC89Ptr_t me);
    char *(ECOCALLMETHOD *tmpnam)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ char *s);
    int (ECOCALLMETHOD *fclose)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream);
    int (ECOCALLMETHOD *fflush)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream);
    FILE *(ECOCALLMETHOD *fopen)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ const char *filename, /* in */ const char *mode);
    FILE *(ECOCALLMETHOD *freopen)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ const char *filename, /* in */ const char *mode, /* in */ FILE *stream);
    void (ECOCALLMETHOD *setbuf)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream, /* in */ char *buf);
    int (ECOCALLMETHOD *setvbuf)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream, /* in */ char *buf, /* in */ int mode, /* in */ size_t size);
    int (ECOCALLMETHOD *fprintf)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream, /* in */ const char *format, ...);
    int (ECOCALLMETHOD *fscanf)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream, /* in */ const char *format, ...);
    int (ECOCALLMETHOD *printf)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ const char *format, ...);
    int (ECOCALLMETHOD *scanf)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ const char *format, ...);
    int (ECOCALLMETHOD *sprintf)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ char *s, /* in */ const char *format, ...);
    int (ECOCALLMETHOD *sscanf)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ const char *s, /* in */ const char *format, ...);
    int (ECOCALLMETHOD *vfprintf)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream, /* in */ const char *format, /* in */ va_list arg);
    int (ECOCALLMETHOD *vprintf)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ const char *format, /* in */ va_list arg);
    int (ECOCALLMETHOD *vsprintf)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ char *s, /* in */ const char *format, /* in */ va_list arg);
    int (ECOCALLMETHOD *fgetc)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream);
    char *(ECOCALLMETHOD *fgets)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ char *s, /* in */ int n, /* in */ FILE *stream);
    int (ECOCALLMETHOD *fputc)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ int c, /* in */ FILE *stream);
    int (ECOCALLMETHOD *fputs)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ const char *s, /* in */ FILE *stream);
    int (ECOCALLMETHOD *getc)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream);
    int (ECOCALLMETHOD *getchar)(/* in */ IEcoStdIOC89Ptr_t me);
    char *(ECOCALLMETHOD *gets)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ char *s);
    int (ECOCALLMETHOD *putc)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ int c, /* in */ FILE *stream);
    int (ECOCALLMETHOD *putchar)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ int c);
    int (ECOCALLMETHOD *puts)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ const char *s);
    int (ECOCALLMETHOD *ungetc)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ int c, /* in */ FILE *stream);
    size_t (ECOCALLMETHOD *fread)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ void *ptr, /* in */ size_t size, /* in */ size_t nmemb, /* in */ FILE *stream);
    size_t (ECOCALLMETHOD *fwrite)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ const void *ptr, /* in */ size_t size, /* in */ size_t nmemb, /* in */ FILE *stream);
    int (ECOCALLMETHOD *fgetpos)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream, /* in */ fpos_t *pos);
    int (ECOCALLMETHOD *fseek)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream, /* in */ long int offset, /* in */ int whence);
    int (ECOCALLMETHOD *fsetpos)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream, /* in */ const fpos_t *pos);
    long int (ECOCALLMETHOD *ftell)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream);
    void (ECOCALLMETHOD *rewind)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream);
    void (ECOCALLMETHOD *clearerr)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream);
    int (ECOCALLMETHOD *feof)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream);
    int (ECOCALLMETHOD *ferror)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ FILE *stream);
    void (ECOCALLMETHOD *perror)(/* in */ IEcoStdIOC89Ptr_t me, /* in */ const char *s);

} IEcoStdIOC89VTbl, *IEcoStdIOC89VTblPtr;

interface IEcoStdIOC89 {
    struct IEcoStdIOC89VTbl *pVTbl;
} IEcoStdIOC89;


#endif /* __I_ECO_STD_IO_C89_H__ */
