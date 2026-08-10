/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   C[!output FIX_PROJECT_NAME]
 * </summary>
 *
 * <description>
 *   This header describes the implementation of the C[!output FIX_PROJECT_NAME] component
 * </description>
 *
 * <author>
 *   Copyright (c) 2026 [!output AUTHOR]. All rights reserved.
 * </author>
 *
 */

#ifndef __C_[!output UPPER_PROJECT_NAME]_HPP__
#define __C_[!output UPPER_PROJECT_NAME]_HPP__

#include "I[!output FIX_PROJECT_NAME].hpp"
#include "IEcoSystem1.hpp"
#include "IdEcoMemoryManager1.hpp"
[!if ADD_CONNECTION_POINTS]
#include "IEcoEnumConnections.hpp"
#include "IEcoConnectionPointContainer.hpp"
#include "C[!output FIX_PROJECT_NAME]ConnectionPoint.hpp"
[!endif]
[!if ADD_CONTAINMENT_OUTER]
/*#include "IEcoXXXX.hpp"*/
[!endif]

[!if ADD_POSTFIX_NAMESPACE]
namespace [!output GUID_CID_NAMESPACE]
{
[!endif]
class C[!output FIX_PROJECT_NAME] :
    public I[!output FIX_PROJECT_NAME]
{

public:
    /* IEcoUnknown */
    virtual int16_t ECOCALLMETHOD QueryInterface(/* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    virtual uint32_t ECOCALLMETHOD AddRef(/* in */ void);
    virtual uint32_t ECOCALLMETHOD Release(/* in */ void);

    /* I[!output FIX_PROJECT_NAME] */
    virtual int16_t ECOCALLMETHOD MyFunction(/* in */ char_t* Name, /* out */ char_t** CopyName);


    /* Инициализация экземпляра */
    int16_t ECOCALLMETHOD Init(/* in */ IEcoUnknown* pIUnkSystem);

    /* Создание экземпляра */
    C[!output FIX_PROJECT_NAME](/* in */ IEcoUnknown* pIUnkSystem, /* in */ IEcoUnknown* pIUnkOuter);
    /* Удаление */
    ~C[!output FIX_PROJECT_NAME]();

private:
    /* Счетчик ссылок */
    uint32_t m_cRef;

    /* Интерфейс для работы с памятью */
    IEcoMemoryAllocator1* m_pIMem;

    /* Системный интерфейс */
    IEcoSystem1* m_pISys;

    /* Данные экземпляра */
    char_t* m_Name;

};
[!if ADD_POSTFIX_NAMESPACE]
} /* namespace [!output GUID_CID_NAMESPACE] */
[!endif]
#endif /* __C_[!output UPPER_PROJECT_NAME]_HPP__ */

