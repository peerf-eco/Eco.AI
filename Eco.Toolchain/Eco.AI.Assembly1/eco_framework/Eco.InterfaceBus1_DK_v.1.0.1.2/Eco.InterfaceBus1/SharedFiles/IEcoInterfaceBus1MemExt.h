/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoInterfaceBus1MemExt
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoInterfaceBus1MemExt
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_INTERFACE_BUS_1_MEMORY_EXTENSION_H__
#define __I_ECO_INTERFACE_BUS_1_MEMORY_EXTENSION_H__

#include "IEcoBase1.h"

/* IEcoInterfaceBus1MemExt IID = {00000000-0000-0000-0000-A00100000101} */
#ifndef __IID_IEcoInterfaceBus1MemExt
static const UGUID IID_IEcoInterfaceBus1MemExt = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xA0, 0x01, 0x00, 0x00, 0x01, 0x01} };
#endif /* __IID_IEcoInterfaceBus1MemExt */

typedef struct IEcoInterfaceBus1MemExt* IEcoInterfaceBus1MemExtPtr_t;

typedef struct IEcoInterfaceBus1MemExtVTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface )(/* in */ IEcoInterfaceBus1MemExtPtr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef )(/* in */ IEcoInterfaceBus1MemExtPtr_t me);
    uint32_t (ECOCALLMETHOD *Release )(/* in */ IEcoInterfaceBus1MemExtPtr_t me);

    /* <метод>
     *   set_Manager
     * </метод>
     * <описание>
     *   Установка поддерживаемого шиной расширения интерфейса дополнительного компонента управления памятью
     * </описание>
     */
    int16_t (ECOCALLMETHOD *set_Manager) (/*in*/ IEcoInterfaceBus1MemExtPtr_t me, /*in*/ const UGUID* rcid);

    /* <метод>
     *   get_Manager
     * </метод>
     * <описание>
     *   Возвращает идентификатор компонента управления памятью
     * </описание>
     */
    const UGUID* (ECOCALLMETHOD *get_Manager) (/*in*/ IEcoInterfaceBus1MemExtPtr_t me);

    /* <метод>
     *   set_ExpandPool
     * </метод>
     * <описание>
     *   Установка разрезрешения == 1, запрета == 0 расширения пула интерфейсной шины
     * </описание>
     */
    int16_t (ECOCALLMETHOD *set_ExpandPool) (/*in*/ IEcoInterfaceBus1MemExtPtr_t me, /*in*/ bool_t bExpandPool);

} IEcoInterfaceBus1MemExtVTbl, *IEcoInterfaceBus1MemExtVTblPtr;

interface IEcoInterfaceBus1MemExt {
    struct IEcoInterfaceBus1MemExtVTbl *pVTbl;
} IEcoInterfaceBus1MemExt;

#endif /* __I_ECO_INTERFACE_BUS_1_MEMORY_EXTENSION_H__ */
