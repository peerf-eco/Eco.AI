/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoEnumConnectionPoints
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoEnumConnectionPoints
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

#ifndef __I_ECO_ENUM_CONNECTION_POINTS_1_HPP__
#define __I_ECO_ENUM_CONNECTION_POINTS_1_HPP__

#include "IEcoBase1.hpp"
#include "IEcoConnectionPoint.hpp"

/* IEcoEnumConnectionPoints IID = 00000004-0000-0000-C000-000000000046 */
#ifndef __IID_IEcoEnumConnectionPoints
static const UGUID IID_IEcoEnumConnectionPoints = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46} };
#endif /* __IID_IEcoEnumConnectionPoints */

interface IEcoEnumConnectionPoints : public IEcoUnknown {
public:
    /* IEcoEnumConnectionPoints */
    virtual int16_t ECOCALLMETHOD Next(/* in */ uint32_t cConnections, /* out */ IEcoConnectionPoint** ppCP, /* out */ uint32_t *pcFetched) = 0;
    virtual int16_t ECOCALLMETHOD Skip(/* in */ uint32_t cConnections) = 0;
    virtual int16_t ECOCALLMETHOD Reset(/* in */ void) = 0;
    virtual int16_t ECOCALLMETHOD Clone(/* out */ IEcoEnumConnectionPoints** ppEnum) = 0;

};

#endif /* __I_ECO_ENUM_CONNECTION_POINTS_1_HPP__ */
