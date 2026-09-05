/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   IEcoConnectionPointContainer
 * </summary>
 *
 * <description>
 *   This header describes the interface IEcoConnectionPointContainer
 * </description>
 *
 * <reference>
 *
 * </reference>
 *
 * <author>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </author>
 *
 */

#ifndef __I_ECO_CONNECTION_POINT_CONTAINER_1_H__
#define __I_ECO_CONNECTION_POINT_CONTAINER_1_H__

#include "IEcoBase1.h"
#include "IEcoEnumConnectionPoints.h"

/* IEcoConnectionPointContainer IID = 00000005-0000-0000-C000-000000000046 */
#ifndef __IID_IEcoConnectionPointContainer
static const UGUID IID_IEcoConnectionPointContainer = { 0x01, 0x10, 0x00, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46 };
#endif /* __IID_IEcoConnectionPointContainer */

typedef struct IEcoConnectionPointContainer* IEcoConnectionPointContainerPtr_t;

typedef struct IEcoConnectionPointContainerVTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoConnectionPointContainerPtr_t me, /* in */ const UGUID* riid, /* out */ void** ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoConnectionPointContainerPtr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoConnectionPointContainerPtr_t me);

    int16_t (ECOCALLMETHOD *EnumConnectionPoints)(/* in */ IEcoConnectionPointContainerPtr_t me, /* out */ struct IEcoEnumConnectionPoints **ppEnum);
    int16_t (ECOCALLMETHOD *FindConnectionPoint)(/* in */ IEcoConnectionPointContainerPtr_t me, /* in */ const UGUID* riid, /* out */ struct IEcoConnectionPoint **ppCP);

} IEcoConnectionPointContainerVTbl;

interface IEcoConnectionPointContainer {
    struct IEcoConnectionPointContainerVTbl *pVTbl;
} IEcoConnectionPointContainer;

#endif /* __I_ECO_CONNECTION_POINT_CONTAINER_1_H__ */
