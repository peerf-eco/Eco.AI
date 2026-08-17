/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoInterfaceBus1NetExt
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoInterfaceBus1NetExt
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_INTERFACE_BUS_1_EXTENSION_H__
#define __I_ECO_INTERFACE_BUS_1_EXTENSION_H__

#include "IEcoBase1.h"

/* IEcoInterfaceBus1NetExt IID = {00000000-0000-0000-0000-A00300000101} */
#ifndef __IID_IEcoInterfaceBus1NetExt
static const UGUID IID_IEcoInterfaceBus1NetExt = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xA0, 0x03, 0x00, 0x00, 0x01, 0x01}};
#endif /* __IID_IEcoInterfaceBus1NetExt */

typedef struct IEcoInterfaceBus1NetExt* IEcoInterfaceBus1NetExtPtr_t;

typedef struct IEcoInterfaceBus1NetExtVTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface )(/* in */ IEcoInterfaceBus1NetExtPtr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef )(/* in */ IEcoInterfaceBus1NetExtPtr_t me);
    uint32_t (ECOCALLMETHOD *Release )(/* in */ IEcoInterfaceBus1NetExtPtr_t me);

    /* <метод>
     *   set_Manager
     * </метод>
     * <описание>
     *   Установка поддерживаемого шиной расширения интерфейса дополнительного компонента управления сетью
     * </описание>
     */
    int16_t (ECOCALLMETHOD *set_Manager) (/*in*/ IEcoInterfaceBus1NetExtPtr_t me, /*in*/ const UGUID* rcid);

    /* <метод>
     *   get_Manager
     * </метод>
     * <описание>
     *   Возвращает идентификатор компонента управления сетью
     * </описание>
     */
    const UGUID* (ECOCALLMETHOD *get_Manager) (/*in*/ IEcoInterfaceBus1NetExtPtr_t me);

    /* <метод>
     *   QueryComponent
     * </метод>
     * <описание>
     *   Запрос экземпляра компонента через сетевое имя
     * </описание>
     */
    int16_t (ECOCALLMETHOD *QueryComponent) (/*in*/ IEcoInterfaceBus1NetExtPtr_t me, /*in*/ char_t* networkname, /*in*/ const UGUID* rcid, /*in*/ IEcoUnknownPtr_t pIUnkOuter, /*in*/ const UGUID* riid, /*out*/ voidptr_t* ppv);

} IEcoInterfaceBus1NetExtVTbl, *IEcoInterfaceBus1NetExtVTblPtr;

interface IEcoInterfaceBus1NetExt {
    struct IEcoInterfaceBus1NetExtVTbl *pVTbl;
} IEcoInterfaceBus1NetExt;

#endif /* __I_ECO_INTERFACE_BUS_1_EXTENSION_H__ */
