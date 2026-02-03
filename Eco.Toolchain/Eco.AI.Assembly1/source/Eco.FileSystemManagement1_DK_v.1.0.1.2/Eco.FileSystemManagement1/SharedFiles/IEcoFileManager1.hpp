/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoFileManager1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoFileManager1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_FILE_MANAGER_1_HPP__
#define __I_ECO_FILE_MANAGER_1_HPP__

#include "IEcoBase1.hpp"
#include "IEcoFile1.hpp"

/* IEcoFileManager1 IID = {00000000-0000-0000-0000-C00000000102} */
#ifndef __IID_IEcoFileManager1
static const UGUID IID_IEcoFileManager1 = {0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00, 0x01, 0x02} };
#endif /* __IID_IEcoFileManager1 */

interface IEcoFileManager1 : public IEcoUnknown {
public:
    /* IEcoFileManager1 */
    virtual IEcoFile1* ECOCALLMETHOD Create(/* in */ char_t* pszName) = 0;
    virtual IEcoFile1* ECOCALLMETHOD Open(/* in */ char_t* pszName) = 0;
    virtual int32_t ECOCALLMETHOD Close(/* in */ IEcoFile1* pIFile) = 0;

};

#endif /* __I_ECO_FILE_MANAGER_1_H__ */
