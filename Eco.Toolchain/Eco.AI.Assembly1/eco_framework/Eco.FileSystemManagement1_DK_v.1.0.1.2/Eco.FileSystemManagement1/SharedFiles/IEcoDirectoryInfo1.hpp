/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoDirectoryInfo1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoDirectoryInfo1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2017 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_DIRECTORY_INFO_1_HPP__
#define __I_ECO_DIRECTORY_INFO_1_HPP__

#include "IEcoBase1.hpp"

/* IEcoDirectoryInfo1 IID = {00000000-0000-0000-0000-C00000000108} */
#ifndef __IID_IEcoDirectoryInfo1
static const UGUID IID_IEcoDirectoryInfo1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x01, 0x08} };
#endif /* __IID_IEcoDirectoryInfo1 */

interface IEcoDirectoryInfo1 : public IEcoUnknown {
public:
    /* IEcoDirectoryInfo1 */
    virtual UGUID* ECOCALLMETHOD get_Id(/* in*/ void) = 0;

};

#endif /* __I_ECO_DIRECTORY_INFO_1_HPP__ */
