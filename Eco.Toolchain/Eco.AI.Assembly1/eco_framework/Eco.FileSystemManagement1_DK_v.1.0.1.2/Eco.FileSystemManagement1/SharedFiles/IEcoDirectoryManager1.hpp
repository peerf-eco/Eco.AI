/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoDirectoryManager1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoDirectoryManager1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2017 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_DIRECTORY_MANAGER_1_HPP__
#define __I_ECO_DIRECTORY_MANAGER_1_HPP__

#include "IEcoBase1.hpp"
#include "IEcoDirectoryInfo1.hpp"

/* IEcoDirectoryManager1 IID = {00000000-0000-0000-0000-C00000000107} */
#ifndef __IID_IEcoDirectoryManager1
static const UGUID IID_IEcoDirectoryManager1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x01, 0x07} };
#endif /* __IID_IEcoDirectoryManager1 */

interface IEcoDirectoryManager1 : public IEcoUnknown {
public:
    /* IEcoDirectoryManager1 */
    virtual IEcoDirectoryInfo1* ECOCALLMETHOD Create(/* in */ char_t* pszName) = 0;
    virtual int32_t ECOCALLMETHOD *Delete(/* in */ char_t* pszName) = 0;

};

#endif /* __I_ECO_DIRECTORY_MANAGER_1_HPP__ */
