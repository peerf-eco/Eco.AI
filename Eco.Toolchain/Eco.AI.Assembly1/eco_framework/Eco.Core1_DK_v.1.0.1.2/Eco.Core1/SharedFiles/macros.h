/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   macros.h
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает макросы
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __ECO_MACROS_H__
#define __ECO_MACROS_H__


#define COMP_CALL(comp, method, ...) comp->pVTbl->method(comp, __VA_ARGS__)
#define COMP_CALL_(comp, method) comp->pVTbl->method

#define I(comp) comp->pVTbl->

#define CONST_CAST(T,EXPR)        ((T)(EXPR))
#define STATIC_CAST(T,EXPR)       ((T)(EXPR))
#define REINTERPRET_CAST(T,EXPR)  ((T)(EXPR))
#define INTEGER_CAST(T,EXPR)      ((T)(uintmax_t)(EXPR))
#define POINTER_CAST(T,EXPR)      ((T)(uintptr_t)(EXPR))

#endif /* __ECO_MACROS_H__ */
