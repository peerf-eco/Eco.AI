/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoInterfaceBus1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoInterfaceBus1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_INTERFACE_BUS_1_H__
#define __I_ECO_INTERFACE_BUS_1_H__

#include "IEcoBase1.h"

/* IEcoInterfaceBus1 IID = {00000000-0000-0000-0000-A00000000101} */
#ifndef __IID_IEcoInterfaceBus1
static const UGUID IID_IEcoInterfaceBus1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xA0, 0x00, 0x00, 0x00, 0x01, 0x01} };
#endif /* __IID_IEcoInterfaceBus1 */

typedef struct IEcoInterfaceBus1* IEcoInterfaceBus1Ptr_t;

typedef struct IEcoInterfaceBus1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface )(/* in */ IEcoInterfaceBus1Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef )(/* in */ IEcoInterfaceBus1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release )(/* in */ IEcoInterfaceBus1Ptr_t me);

    /* IEcoInterfaceBus1 */

    /* <метод>
     *   Init
     * </метод>
     * <описание>
     *   Инициализация интерфейсной шины
     * </описание>
     */
    int16_t (ECOCALLMETHOD *Init)(/*in*/ IEcoInterfaceBus1Ptr_t me);

    /* <метод>
     *   InitWith
     * </метод>
     * <описание>
     *   Инициализация интерфейсной шины
     * </описание>
     */
    int16_t (ECOCALLMETHOD *InitWith)(/*in*/ IEcoInterfaceBus1Ptr_t me, /*in*/ void* heapStartAddress, /*in*/ uint32_t size);

    /* <метод>
     *   RegisterComponent
     * </метод>
     * <описание>
     *   Регистрация компонента
     * </описание>
     */
    int16_t (ECOCALLMETHOD *RegisterComponent) (/*in*/ IEcoInterfaceBus1Ptr_t me, /*in*/ const UGUID* rcid, /*in*/ IEcoUnknownPtr_t pIFactory);

    /* <метод>
     *   UnRegisterComponent
     * </метод>
     * <описание>
     *   Отмена регистрации компонента
     * </описание>
     */
    int16_t (ECOCALLMETHOD *UnRegisterComponent) (/*in*/ IEcoInterfaceBus1Ptr_t me, /*in*/ const UGUID* rcid);

    /* <метод>
     *   QueryComponent
     * </метод>
     * <описание>
     *   Запрос экземпляра компонента
     * </описание>
     */
    int16_t (ECOCALLMETHOD *QueryComponent) (/*in*/ IEcoInterfaceBus1Ptr_t me, /*in*/ const UGUID* rcid, /*in*/ IEcoUnknownPtr_t pIUnkOuter, /*in*/ const UGUID* riid, /*out*/ voidptr_t* ppv);

} IEcoInterfaceBus1VTbl, *IEcoInterfaceBus1VTblPtr;

interface IEcoInterfaceBus1 {
    struct IEcoInterfaceBus1VTbl *pVTbl;
} IEcoInterfaceBus1;

#endif /* __I_ECO_INTERFACE_BUS_1_H__ */
