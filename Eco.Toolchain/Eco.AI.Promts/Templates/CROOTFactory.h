/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]Factory
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

#ifndef __C_[!output UPPER_PROJECT_NAME]_FACTORY_H__
#define __C_[!output UPPER_PROJECT_NAME]_FACTORY_H__

#include "IEcoSystem1.h"

typedef struct C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]Factory {

    /* IEcoComponentFactory interface function table */
    IEcoComponentFactoryVTbl* m_pVTblICF;

    /* Reference counter */
    uint32_t m_cRef;

    /* Component data for the factory */
    char_t m_Name[64];
    char_t m_Version[16];
    char_t m_Manufacturer[64];

} C[!output FIX_PROJECT_NAME][!output GUID_CID_NAMESPACE]Factory;

#endif /* __C_[!output UPPER_PROJECT_NAME]_FACTORY_H__ */
