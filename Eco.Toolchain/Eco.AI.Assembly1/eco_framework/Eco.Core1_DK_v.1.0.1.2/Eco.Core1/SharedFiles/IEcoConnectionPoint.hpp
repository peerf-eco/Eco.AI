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

#ifndef __I_ECO_CONNECTION_POINT_1_HPP__
#define __I_ECO_CONNECTION_POINT_1_HPP__

#include "IEcoBase1.hpp"

/* IEcoConnectionPoint IID = 00000003-0000-0000-C000-000000000046 */
#ifndef __IID_IEcoConnectionPoint
static const UGUID IID_IEcoConnectionPoint = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46} };
#endif /* __IID_IEcoConnectionPoint */

interface IEcoConnectionPoint : public IEcoUnknown {
public:
    /* IEcoConnectionPoint */
    virtual int16_t ECOCALLMETHOD GetConnectionInterface(/* out */ UGUID *pIID) = 0;
    virtual int16_t ECOCALLMETHOD GetConnectionPointContainer(/* out */ IEcoConnectionPointContainer** ppCPC) = 0;
    virtual int16_t ECOCALLMETHOD Advise(/* in */ IEcoUnknown* pUnkSink, /* out */ uint32_t *pcCookie) = 0;
    virtual int16_t ECOCALLMETHOD Unadvise(/* in */ uint32_t cCookie) = 0;
    virtual int16_t ECOCALLMETHOD EnumConnections(/* out */ IEcoEnumConnections** ppEnum) = 0;

};

#endif /* __I_ECO_CONNECTION_POINT_1_HPP__ */
