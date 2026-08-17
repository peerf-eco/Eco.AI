/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoMemoryManager1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoMemoryManager1
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

#ifndef __I_ECO_MEMORY_MANAGER_1_HPP__
#define __I_ECO_MEMORY_MANAGER_1_HPP__

#include "IEcoBase1.hpp"
#include "IEcoMemoryAllocator1.hpp"

typedef struct ECOMEMORYMANAGER1BLOCK {
    uint32_t lowAddr;
    uint32_t highAddr;
    uint32_t size;
} ECOMEMORYMANAGER1BLOCK;

typedef struct ECOMEMORYMANAGER1STATUS {
    uint32_t lowAddr;
    uint32_t highAddr;
    uint32_t totalSize;
    uint32_t freeSize;
    uint32_t usedBlocks;
} ECOMEMORYMANAGER1STATUS;

/* IEcoMemoryManager1 IID = {00000000-0000-0000-0000-B00000000101} */
#ifndef __IID_IEcoMemoryManager1
static const UGUID IID_IEcoMemoryManager1 = { 0x01, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xB0, 0x00, 0x00, 0x00, 0x01, 0x01};
#endif /* __IID_IEcoMemoryManager1 */

interface IEcoMemoryManager1 : public IEcoUnknown {

    /* IEcoMemoryManager1 */
    virtual int16_t ECOCALLMETHOD Init(/* in */ void* startAddress, /* in */ uint32_t size) = 0;
    virtual bool_t ECOCALLMETHOD get_Status(/* in | out */ ECOMEMORYMANAGER1STATUS* status) = 0;
    virtual bool_t ECOCALLMETHOD get_UsedBlocks(/* in | out */ ECOMEMORYMANAGER1BLOCK* blocks, /* in | out */ uint32_t* sizeInBlocks) = 0;
};

#endif /* __I_ECO_MEMORY_MANAGER_1_HPP__ */

