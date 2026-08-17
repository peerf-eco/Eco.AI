/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   ErrEcoCodes
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает коды ошибок
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

#ifndef __ERR_ECO_CODES_H__
#define __ERR_ECO_CODES_H__

/*
 * <код ошибки>
 *   ERR_ECO_SUCCESES
 * </код ошибки>
 *
 * <описание>
 *   Выполнено успешно.
 * </описание>
 */
#define ERR_ECO_SUCCESES                0x0000
#define ERR_ECO_OK                      ERR_ECO_SUCCESES

/*
 * <код ошибки>
 *   ERR_ECO_USER
 * </код ошибки>
 *
 * <описание>
 *   Коды ошибок определенные пользователем.
 * </описание>
 */
#define ERR_ECO_USER                    0x0002

/*
 * <код ошибки>
 *   ERR_ECO_UNEXPECTED
 * </код ошибки>
 *
 * <описание>
 *   Непредвиденное условие. Катастрофический сбой.
 * </описание>
 */
#define ERR_ECO_UNEXPECTED              0xFFFF

/*
 * <код ошибки>
 *   ERR_ECO_POINTER
 * </код ошибки>
 *
 * <описание>
 *   Было передано неправильное значение указателя.
 * </описание>
 */
#define ERR_ECO_POINTER                 0xFFEE

/*
 * <код ошибки>
 *   ERR_ECO_NOINTERFACE
 * </код ошибки>
 *
 * <описание>
 *  Такой интерфейс не поддерживается.
 * </описание>
 */
#define ERR_ECO_NOINTERFACE             0xFFED

/*
 * <код ошибки>
 *   ERR_ECO_NOSYSTEM
 * </код ошибки>
 *
 * <описание>
 *  Системный интерфейс не поддерживается.
 * </описание>
 */
#define ERR_ECO_NOSYSTEM                0xFFEC

/*
 * <код ошибки>
 *   ERR_ECO_NOBUS
 * </код ошибки>
 *
 * <описание>
 *  Интерфейсная шина не поддерживается.
 * </описание>
 */
#define ERR_ECO_NOBUS                   0xFFEB

/*
 * <код ошибки>
 *   ERR_ECO_NOAGGREGATION
 * </код ошибки>
 *
 * <описание>
 *  Агрегирование не поддерживается.
 * </описание>
 */
#define ERR_ECO_NOAGGREGATION           0xFFEA

/*
 * <код ошибки>
 *   ERR_ECO_COMPONENT_NOTFOUND
 * </код ошибки>
 *
 * <описание>
 *  Компонент не найден.
 * </описание>
 */
#define ERR_ECO_COMPONENT_NOTFOUND      0xFFE9

/*
 * <код ошибки>
 *   ERR_ECO_OUTOFMEMORY
 * </код ошибки>
 *
 * <описание>
 *  Сбой при попытке выделения памяти.
 * </описание>
 */
#define ERR_ECO_OUTOFMEMORY             0xFFE8

/*
 * <код ошибки>
 *   ERR_ECO_MEMMGR_NOTREG
 * </код ошибки>
 *
 * <описание>
 *  Компонент управления памятью не зарегистрирован.
 * </описание>
 */
#define ERR_ECO_MEMMGR_NOTREG           0xFFE7

/*
 * <код ошибки>
 *   ERR_ECO_GET_MEMORY_ALLOCATOR
 * </код ошибки>
 *
 * <описание>
 *  Сбой с получением распределителя памяти.
 * </описание>
 */
#define ERR_ECO_GET_MEMORY_ALLOCATOR    0xFFE6

/*
 * <код ошибки>
 *   ERR_ECO_FAIL
 * </код ошибки>
 *
 * <описание>
 *   Неопознанная ошибка.
 * </описание>
 */
#define ERR_ECO_FAIL                    0xFFE5

/*
 * <код ошибки>
 *   ERR_ECO_NOTIMPL
 * </код ошибки>
 *
 * <описание>
 *   Не реализовано.
 * </описание>
 */
#define ERR_ECO_NOTIMPL                 0xFFE4

/*
 * <код ошибки>
 *   ERR_ECO_INVALIDARG
 * </код ошибки>
 *
 * <описание>
 *   Один или несколько аргументов являются недопустимыми.
 * </описание>
 */
#define ERR_ECO_INVALIDARG               0xFFE3

/*
 * <код ошибки>
 *   ERR_ECO_FILEMGR_NOTREG
 * </код ошибки>
 *
 * <описание>
 *  Компонент управления файловой системой не зарегистрирован.
 * </описание>
 */
#define ERR_ECO_FILEMGR_NOTREG           0xFFE2

/*
 * <код ошибки>
 *   ERR_ECO_NETMGR_NOTREG
 * </код ошибки>
 *
 * <описание>
 *  Компонент управления сетью не зарегистрирован.
 * </описание>
 */
#define ERR_ECO_NETMGR_NOTREG           0xFFE1

#endif /* __ERR_ECO_CODES_H__ */
