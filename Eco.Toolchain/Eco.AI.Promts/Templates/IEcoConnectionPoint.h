/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   IEcoConnectionPoint
 * </summary>
 *
 * <description>
 *   This header describes the interface IEcoConnectionPoint
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

#ifndef __I_ECO_CONNECTION_POINT_1_H__
#define __I_ECO_CONNECTION_POINT_1_H__

#include "IEcoBase1.h"

/* IEcoConnectionPoint IID = 00000003-0000-0000-C000-000000000046 */
#ifndef __IID_IEcoConnectionPoint
static const UGUID IID_IEcoConnectionPoint = { 0x01, 0x10, 0x00, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46 };
#endif /* __IID_IEcoConnectionPoint */

struct IEcoConnectionPointContainer;

typedef struct IEcoConnectionPoint* IEcoConnectionPointPtr_t;

typedef struct IEcoConnectionPointVTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface )(/* in */ IEcoConnectionPointPtr_t me, /* in */ const UGUID* riid, /* out */ void** ppv);
    uint32_t (ECOCALLMETHOD *AddRef )(/* in */ IEcoConnectionPointPtr_t me);
    uint32_t (ECOCALLMETHOD *Release )(/* in */ IEcoConnectionPointPtr_t me);

    int16_t (ECOCALLMETHOD *GetConnectionInterface )(/* in */ IEcoConnectionPointPtr_t me, /* out */ UGUID *pIID);
    int16_t (ECOCALLMETHOD *GetConnectionPointContainer )(/* in */ IEcoConnectionPointPtr_t me, /* out */ struct IEcoConnectionPointContainer **ppCPC);
    int16_t (ECOCALLMETHOD *Advise)(/* in */ IEcoConnectionPointPtr_t me, /* in */ struct IEcoUnknown *pUnkSink, /* out */ uint32_t *pcCookie);
    int16_t (ECOCALLMETHOD *Unadvise)(/* in */ IEcoConnectionPointPtr_t me, /* in */ uint32_t cCookie);
    int16_t (ECOCALLMETHOD *EnumConnections)(/* in */ IEcoConnectionPointPtr_t me, /* out */ struct IEcoEnumConnections **ppEnum);

} IEcoConnectionPointVTbl;

interface IEcoConnectionPoint {
    struct IEcoConnectionPointVTbl *pVTbl;
} IEcoConnectionPoint;

#endif /* __I_ECO_CONNECTION_POINT_1_H__ */
