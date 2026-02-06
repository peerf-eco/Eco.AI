/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoMemoryAllocator1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoMemoryAllocator1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_MEMORY_ALLOCATOR_1_HPP__
#define __I_ECO_MEMORY_ALLOCATOR_1_HPP__

#include "IEcoBase1.hpp"

/* IEcoMemoryAllocator1 IID = {00000000-0000-0000-0000-B00000000102} */
#ifndef __IID_IEcoMemoryAllocator1
static const UGUID IID_IEcoMemoryAllocator1 = { 0x01, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xB0, 0x00, 0x00, 0x00, 0x01, 0x02 };
#endif /* __IID_IEcoMemoryAllocator1 */

interface IEcoMemoryAllocator1 : public IEcoUnknown {

    /* IEcoMemoryAllocator */
    virtual void* ECOCALLMETHOD Alloc(/* in */ uint32_t size) = 0;
    virtual void ECOCALLMETHOD Free(/* in */ void *pv) = 0;
    virtual void* ECOCALLMETHOD Realloc(/* in */ void *pv, /* in */ uint32_t size) = 0;
    virtual void* ECOCALLMETHOD Copy(/* in */ void *pvDst, /* in */ void *pvSrc, /* in */ uint32_t size) = 0;
    virtual void* ECOCALLMETHOD Fill(/* in */ void *pvDst, /* in */ char_t Fill, /* in */ uint32_t size) = 0;
    virtual int16_t ECOCALLMETHOD Compare(/* in */ void *pv1, /* in */ void *pv2, /* in */ uint32_t size) = 0;
    virtual uint32_t ECOCALLMETHOD RetrieveSize(/* in */ void *pv) = 0;
};

#endif /* __I_ECO_MEMORY_ALLOCATOR_1_HPP__ */
