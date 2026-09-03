/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoFileInfo1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoFileInfo1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2017 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_FILE_INFO_1_HPP__
#define __I_ECO_FILE_INFO_1_HPP__

#include "IEcoBase1.hpp"

/* IEcoFileInfo1 IID = {00000000-0000-0000-0000-C00000000103} */
#ifndef __IID_IEcoFileInfo1
static const UGUID IID_IEcoFileInfo1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x01, 0x03} };
#endif /* __IID_IEcoFileInfo1 */

interface IEcoFileInfo1 : public IEcoUnknown {
public:
    /* IEcoFileInfo1 */
    virtual UGUID* ECOCALLMETHOD get_Id(/* in*/ void) = 0;

};

#endif /* __I_ECO_FILE_INFO_1_HPP__ */
