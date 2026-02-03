/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoInterfaceBus1FileExt
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoInterfaceBus1FileExt
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_INTERFACE_BUS_1_FILE_EXTENSION_H__
#define __I_ECO_INTERFACE_BUS_1_FILE_EXTENSION_H__

#include "IEcoBase1.h"

/* IEcoInterfaceBus1FileExt IID = {00000000-0000-0000-0000-A00200000101} */
#ifndef __IID_IEcoInterfaceBus1FileExt
static const UGUID IID_IEcoInterfaceBus1FileExt = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xA0, 0x02, 0x00, 0x00, 0x01, 0x01} };
#endif /* __IID_IEcoInterfaceBus1FileExt */

typedef struct IEcoInterfaceBus1FileExt* IEcoInterfaceBus1FileExtPtr_t;

typedef struct IEcoInterfaceBus1FileExtVTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface )(/* in */ IEcoInterfaceBus1FileExtPtr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef )(/* in */ IEcoInterfaceBus1FileExtPtr_t me);
    uint32_t (ECOCALLMETHOD *Release )(/* in */ IEcoInterfaceBus1FileExtPtr_t me);

    /* <метод>
     *   set_Manager
     * </метод>
     * <описание>
     *   Установка поддерживаемого шиной расширения интерфейса дополнительного компонента управления файловой системой
     * </описание>
     */
    int16_t (ECOCALLMETHOD *set_Manager) (/*in*/ IEcoInterfaceBus1FileExtPtr_t me, /*in*/ const UGUID* rcid);

    /* <метод>
     *   get_Manager
     * </метод>
     * <описание>
     *   Возвращает идентификатор компонента управления файловой системой
     * </описание>
     */
    const UGUID* (ECOCALLMETHOD *get_Manager) (/*in*/ IEcoInterfaceBus1FileExtPtr_t me);

    /* <метод>
     *   set_SearchPath
     * </метод>
     * <описание>
     *   Установка пути поиска компонетов
     * </описание>
     */
    int16_t (ECOCALLMETHOD *set_SearchPath) (/*in*/ IEcoInterfaceBus1FileExtPtr_t me, /*in*/ char_t* path);

    /* <метод>
     *   get_SearchPath
     * </метод>
     * <описание>
     *   Возвращает путm поиска компонетов
     * </описание>
     */
    char_t* (ECOCALLMETHOD *get_SearchPath) (/*in*/ IEcoInterfaceBus1FileExtPtr_t me);

    /* <метод>
     *   RegisterComponent
     * </метод>
     * <описание>
     *   Регистрация компонента
     * </описание>
     */
    int16_t (ECOCALLMETHOD *RegisterComponent) (/*in*/ IEcoInterfaceBus1FileExtPtr_t me, /*in*/ const UGUID* rcid, /*in*/ char_t* filename);

    /* <метод>
     *   QueryComponent
     * </метод>
     * <описание>
     *   Запрос экземпляра компонента через имя файла
     * </описание>
     */
    int16_t (ECOCALLMETHOD *QueryComponent) (/*in*/ IEcoInterfaceBus1FileExtPtr_t me, /*in*/ char_t* filename, /*in*/ const UGUID* rcid, /*in*/ IEcoUnknownPtr_t pIUnkOuter, /*in*/ const UGUID* riid, /*out*/ voidptr_t* ppv);

} IEcoInterfaceBus1FileExtVTbl, *IEcoInterfaceBus1FileExtVTblPtr;

interface IEcoInterfaceBus1FileExt {
    struct IEcoInterfaceBus1FileExtVTbl *pVTbl;
} IEcoInterfaceBus1FileExt;

#endif /* __I_ECO_INTERFACE_BUS_1_FILE_EXTENSION_H__ */
