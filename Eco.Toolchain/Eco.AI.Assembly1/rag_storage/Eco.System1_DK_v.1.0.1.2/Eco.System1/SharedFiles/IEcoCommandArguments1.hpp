/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoCommandArguments1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoCommandArguments1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_COMMAND_ARGUMENTS_1_HPP__
#define __I_ECO_COMMAND_ARGUMENTS_1_HPP__

#include "IEcoBase1.hpp"

/* IEcoCommandArguments1 IID = {00000000-0000-0000-0000-000000000110} */
#ifndef __IID_IEcoCommandArguments1
static const UGUID IID_IEcoCommandArguments1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x10}};
#endif /* __IID_IEcoCommandArguments1 */

interface IEcoCommandArguments1 : public IEcoUnknown {
public:
    /* IEcoCommandArguments1 */
    virtual int16_t ECOCALLMETHOD get_Count(/* in*/ void) = 0;
    virtual char_t** ECOCALLMETHOD get_Args(/* in*/ void) = 0;
    virtual char_t*(ECOCALLMETHOD get_Path(/* in*/ void) = 0;
    virtual char_t* ECOCALLMETHOD get_Arg(/* in */ int16_t index) = 0;

};

#endif /* __I_ECO_COMMAND_ARGUMENTS_1_HPP__ */
