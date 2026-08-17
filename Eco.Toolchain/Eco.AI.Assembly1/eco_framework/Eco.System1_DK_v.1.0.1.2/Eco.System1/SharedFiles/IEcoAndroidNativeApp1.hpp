/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoAndroidNativeApp1
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов IEcoAndroidNativeApp1
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_ANDROID_NATIVE_APP_1_HPP__
#define __I_ECO_ANDROID_NATIVE_APP_1_HPP__

#include "IEcoBase1.hpp"

/* Android NDK r15 и выше */
#include <android/configuration.h>
#include <android/looper.h>
#include <android/native_activity.h>

/* IEcoAndroidNativeApp1 IID = {41D50AF9-2EED-4355-99E0-C40BC3AFBF43} */
#ifndef __IID_IEcoAndroidNativeApp1
static const UGUID IID_IEcoAndroidNativeApp1 = {0x01, 0x10, {0x41, 0xD5, 0x0A, 0xF9, 0x2E, 0xED, 0x43, 0x55, 0x99, 0xE0, 0xC4, 0x0B, 0xC3, 0xAF, 0xBF, 0x43}};
#endif /* __IID_IEcoAndroidNativeApp1 */

interface IEcoAndroidNativeApp1 : public IEcoUnknown {
public:
    /* IEcoAndroidNativeApp1 */
    virtual int16_t ECOCALLMETHOD get_Activity(/* out */ ANativeActivity** activity, /* out */ void** savedState, /* out */ size_t* savedStateSize) = 0;
    virtual int16_t ECOCALLMETHOD get_Window(/* out */ ANativeWindow** window) = 0;
};

#endif /* __I_ECO_ANDROID_NATIVE_APP_1_HPP__ */
