/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoDriveManager1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoDriveManager1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2017 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_DRIVE_MANAGER_1_HPP__
#define __I_ECO_DRIVE_MANAGER_1_HPP__

#include "IEcoBase1.hpp"
#include "IEcoDriveInfo1.hpp"

/* IEcoDriveManager1 IID = {00000000-0000-0000-0000-C00000000105} */
#ifndef __IID_IEcoDriveManager1
static const UGUID IID_IEcoDriveManager1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x01, 0x05} };
#endif /* __IID_IEcoDriveManager1 */

interface IEcoDriveManager1 : public IEcoUnknown {
public:
    /* IEcoDriveManager1 */
    virtual IEcoDriveInfo1* ECOCALLMETHOD get_Drive(/* in */ char_t* pszName) = 0;

};

#endif /* __I_ECO_DIRECTORY_MANAGER_1_HPP__ */
