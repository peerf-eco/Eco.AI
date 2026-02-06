/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoDriveInfo1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoDriveInfo1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2017 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_DRIVE_INFO_1_HPP__
#define __I_ECO_DRIVE_INFO_1_HPP__

#include "IEcoBase1.hpp"

/* IEcoDriveInfo1 IID = {00000000-0000-0000-0000-C00000000106} */
#ifndef __IID_IEcoDriveInfo1
static const UGUID IID_IEcoDriveInfo1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x01, 0x06} };
#endif /* __IID_IEcoDriveInfo1 */

interface IEcoDriveInfo1 : public IEcoUnknown {
public:
    /* IEcoDriveInfo1 */
    virtual UGUID* ECOCALLMETHOD get_Id(/* in*/ void) = 0;

};

#endif /* __I_ECO_DRIVE_INFO_1_HPP__ */
