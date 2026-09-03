/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoSystemInformation1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoSystemInformation1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_SYSTEM_INFORMATION_1_HPP__
#define __I_ECO_SYSTEM_INFORMATION_1_HPP__

#include "IEcoBase1.hpp"

/* IEcoSystemInformation1 IID = {00000000-0000-0000-0000-0000000001FF} */
#ifndef __IID_IEcoSystemInformation1
static const UGUID IID_IEcoSystemInformation1 = {0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0xFF}};
#endif /* __IID_IEcoSystemInformation1 */

interface IEcoSystemInformation1 : public IEcoUnknown {
public:
    /* IEcoSystemInformation1 */
    virtual char_t* ECOCALLMETHOD get_Name(/* in*/ void) = 0;
    virtual char_t* ECOCALLMETHOD get_Id(/* in*/ void) = 0;
};

#endif /* __I_ECO_SYSTEM_INFORMATION_1_HPP__ */
