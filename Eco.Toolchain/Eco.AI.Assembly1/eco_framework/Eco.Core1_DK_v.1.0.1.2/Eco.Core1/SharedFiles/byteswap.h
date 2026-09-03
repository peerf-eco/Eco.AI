/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   byteswap.h
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает базовые определения данных
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __ECO_BYTE_SWAP_H__
#define __ECO_BYTE_SWAP_H__

#ifdef BYTESWAP_UTILITY
#define byteswap_uint16_t(val) \
    (uint16_t)(((uint16_t)val << 8) | ((uint16_t)val >> 8 ))
#define byteswap_int16_t(val) \
    (int16_t)(((int16_t)val << 8) | ((int16_t)val >> 8 ) & 0xFF)
#define byteswap_uint32_t(val) \
    (uint32_t)((((((uint32_t)val << 8) & 0xFF00FF00 ) | (((uint32_t)val >> 8) & 0x00FF00FF )) << 16) | \
    (((((uint32_t)val << 8) & 0xFF00FF00 ) | (((uint32_t)val >> 8) & 0x00FF00FF )) >> 16))
#define byteswap_int32_t(val) \
    (int32_t)((((((int32_t)val << 8) & 0xFF00FF00 ) | (((int32_t)val >> 8) & 0x00FF00FF )) << 16) | \
    (((((int32_t)val << 8) & 0xFF00FF00 ) | (((int32_t)val >> 8) & 0x00FF00FF )) >> 16) & 0xFFFF )
#define byteswap_uint64_t(val) \
    (uint64_t)(((((((((uint64_t)val << 8) & 0xFF00FF00FF00FF00ULL ) | (((uint64_t)val >> 8) & 0x00FF00FF00FF00FFULL)) << 16) & 0xFFFF0000FFFF0000ULL ) | \
    ((((((uint64_t)val << 8) & 0xFF00FF00FF00FF00ULL ) | (((uint64_t)val >> 8) & 0x00FF00FF00FF00FFULL)) >> 16) & 0x0000FFFF0000FFFFULL)) << 32) | \
    ((((((((uint64_t)val << 8) & 0xFF00FF00FF00FF00ULL ) | (((uint64_t)val >> 8) & 0x00FF00FF00FF00FFULL)) << 16) & 0xFFFF0000FFFF0000ULL ) | \
    ((((((uint64_t)val << 8) & 0xFF00FF00FF00FF00ULL ) | (((uint64_t)val >> 8) & 0x00FF00FF00FF00FFULL)) >> 16) & 0x0000FFFF0000FFFFULL)) >> 32))
#define byteswap_int64_t(val) \
    (int64_t)(((((((((uint64_t)val << 8) & 0xFF00FF00FF00FF00ULL ) | (((int64_t)val >> 8) & 0x00FF00FF00FF00FFULL)) << 16) & 0xFFFF0000FFFF0000ULL ) | \
    ((((((int64_t)val << 8) & 0xFF00FF00FF00FF00ULL ) | (((int64_t)val >> 8) & 0x00FF00FF00FF00FFULL)) >> 16) & 0x0000FFFF0000FFFFULL)) << 32) | \
    ((((((((int64_t)val << 8) & 0xFF00FF00FF00FF00ULL ) | (((int64_t)val >> 8) & 0x00FF00FF00FF00FFULL)) << 16) & 0xFFFF0000FFFF0000ULL ) | \
    ((((((int64_t)val << 8) & 0xFF00FF00FF00FF00ULL ) | (((int64_t)val >> 8) & 0x00FF00FF00FF00FFULL)) >> 16) & 0x0000FFFF0000FFFFULL)) >> 32) & 0xFFFFFFFFULL)

#endif

#endif /* __ECO_BYTE_SWAP_H__ */
