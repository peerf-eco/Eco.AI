/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoConnectionPoint
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoConnectionPoint
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

#ifndef __I_ECO_CONNECTION_POINT_1_H__
#define __I_ECO_CONNECTION_POINT_1_H__

#include "IEcoBase1.h"

/* IEcoConnectionPoint IID = 00000003-0000-0000-C000-000000000046 */
#ifndef __IID_IEcoConnectionPoint
static const UGUID IID_IEcoConnectionPoint = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46} };
#endif /* __IID_IEcoConnectionPoint */

typedef struct IEcoConnectionPointContainer* IEcoConnectionPointContainerPtr_t;
typedef struct IEcoConnectionPoint* IEcoConnectionPointPtr_t;
typedef struct IEcoEnumConnections* IEcoEnumConnectionsPtr_t;

typedef struct IEcoConnectionPointVTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface )(/* in */ IEcoConnectionPointPtr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef )(/* in */ IEcoConnectionPointPtr_t me);
    uint32_t (ECOCALLMETHOD *Release )(/* in */ IEcoConnectionPointPtr_t me);

    int16_t (ECOCALLMETHOD *GetConnectionInterface )(/* in */ IEcoConnectionPointPtr_t me, /* out */ UGUID *pIID);
    int16_t (ECOCALLMETHOD *GetConnectionPointContainer )(/* in */ IEcoConnectionPointPtr_t me, /* out */ IEcoConnectionPointContainerPtr_t* ppCPC);
    int16_t (ECOCALLMETHOD *Advise)(/* in */ IEcoConnectionPointPtr_t me, /* in */ IEcoUnknownPtr_t pUnkSink, /* out */ uint32_t *pcCookie);
    int16_t (ECOCALLMETHOD *Unadvise)(/* in */ IEcoConnectionPointPtr_t me, /* in */ uint32_t cCookie);
    int16_t (ECOCALLMETHOD *EnumConnections)(/* in */ IEcoConnectionPointPtr_t me, /* out */ IEcoEnumConnectionsPtr_t* ppEnum);

} IEcoConnectionPointVTbl;

interface IEcoConnectionPoint {
    struct IEcoConnectionPointVTbl *pVTbl;
} IEcoConnectionPoint;

#endif /* __I_ECO_CONNECTION_POINT_1_H__ */
