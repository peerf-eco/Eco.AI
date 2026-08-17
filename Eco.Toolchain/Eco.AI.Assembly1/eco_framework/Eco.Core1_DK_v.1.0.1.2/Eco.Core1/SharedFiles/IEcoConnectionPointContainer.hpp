/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoConnectionPointContainer
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoConnectionPointContainer
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

#ifndef __I_ECO_CONNECTION_POINT_CONTAINER_1_HPP__
#define __I_ECO_CONNECTION_POINT_CONTAINER_1_HPP__

#include "IEcoBase1.hpp"
#include "IEcoEnumConnectionPoints.hpp"

/* IEcoConnectionPointContainer IID = 00000005-0000-0000-C000-000000000046 */
#ifndef __IID_IEcoConnectionPointContainer
static const UGUID IID_IEcoConnectionPointContainer = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46} };
#endif /* __IID_IEcoConnectionPointContainer */

interface IEcoConnectionPointContainer : public IEcoUnknown {
public:
    /* IEcoConnectionPointContainer */
    virtual int16_t ECOCALLMETHOD EnumConnectionPoints(/* out */ IEcoEnumConnectionPoints** ppEnum) = 0;
    virtual int16_t ECOCALLMETHOD FindConnectionPoint(/* in */ const UGUID* riid, /* out */ IEcoConnectionPoint** ppCP) = 0;

};

#endif /* __I_ECO_CONNECTION_POINT_CONTAINER_1_HPP__ */
