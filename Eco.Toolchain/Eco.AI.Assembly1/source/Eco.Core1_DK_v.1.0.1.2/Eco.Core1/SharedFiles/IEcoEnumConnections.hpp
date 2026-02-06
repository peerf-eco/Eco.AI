/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoEnumConnections
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoEnumConnections
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

#ifndef __I_ECO_ENUM_CONNECTIONS_1_HPP__
#define __I_ECO_ENUM_CONNECTIONS_1_HPP__

#include "IEcoBase1.hpp"

typedef struct EcoConnectionData {
    IEcoUnknown *pUnk;
    uint32_t cCookie;
} EcoConnectionData;

/* IEcoEnumConnections IID = 00000002-0000-0000-C000-000000000046 */
#ifndef __IID_IEcoEnumConnections
static const UGUID IID_IEcoEnumConnections = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46} };
#endif /* __IID_IEcoEnumConnections */

interface IEcoEnumConnections : public IEcoUnknown {
public:
    /* IEcoEnumConnections */
    virtual int16_t ECOCALLMETHOD Next(/* in */ uint32_t cConnections, /* out */ struct EcoConnectionData *rgcd, /* out */ uint32_t *pcFetched) = 0;
    virtual int16_t ECOCALLMETHOD Skip(/* in */ uint32_t cConnections) = 0;
    virtual int16_t ECOCALLMETHOD Reset(/* in */ void) = 0;
    virtual int16_t ECOCALLMETHOD Clone(/* out */ IEcoEnumConnections** ppEnum) = 0;

};

#endif /* __I_ECO_ENUM_CONNECTIONS_1_HPP__ */
