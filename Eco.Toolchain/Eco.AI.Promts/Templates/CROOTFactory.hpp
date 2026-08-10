/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   C[!output FIX_PROJECT_NAME]Factory
 * </summary>
 *
 * <description>
 *   This header describes the implementation of the factory for the component
 * </description>
 *
 * <author>
 *   Copyright (c) 2026 [!output AUTHOR]. All rights reserved.
 * </author>
 *
 */

#ifndef __C_[!output UPPER_PROJECT_NAME]_FACTORY_HPP__
#define __C_[!output UPPER_PROJECT_NAME]_FACTORY_HPP__

#include "IEcoSystem1.hpp"

[!if ADD_POSTFIX_NAMESPACE]
namespace [!output GUID_CID_NAMESPACE]
{
[!endif]
class C[!output FIX_PROJECT_NAME]Factory :
    public IEcoComponentFactory
{
public:
    /* IEcoUnknown */
    virtual int16_t ECOCALLMETHOD QueryInterface(/* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    virtual uint32_t ECOCALLMETHOD AddRef(/* in */ void);
    virtual uint32_t ECOCALLMETHOD Release(/* in */ void);

    /* IEcoComponentFactory */
    virtual int16_t ECOCALLMETHOD Alloc(/* in */ IEcoUnknown *pISystem, /* in */ IEcoUnknown *pIUnknownOuter, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    virtual int16_t ECOCALLMETHOD Init(/* in */ IEcoUnknown *pISystem, /* in */ voidptr_t pv);
    virtual char_t* ECOCALLMETHOD get_Name(/* in */ void);
    virtual char_t* ECOCALLMETHOD get_Version(/* in */ void);
    virtual char_t* ECOCALLMETHOD get_Manufacturer(/* in */ void);

private:

    /* Счетчик ссылок */
    uint32_t m_cRef;

    /* Данные компонентов для фабрики */
    char_t m_Name[64];
    char_t m_Version[16];
    char_t m_Manufacturer[64];

};
[!if ADD_POSTFIX_NAMESPACE]
} /* namespace [!output GUID_CID_NAMESPACE] */
[!endif]
#endif /* __C_[!output UPPER_PROJECT_NAME]_FACTORY_HPP__ */
