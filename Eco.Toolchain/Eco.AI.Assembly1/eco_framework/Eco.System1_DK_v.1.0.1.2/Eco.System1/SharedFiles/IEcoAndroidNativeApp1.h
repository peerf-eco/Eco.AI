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

#ifndef __I_ECO_ANDROID_NATIVE_APP_1_H__
#define __I_ECO_ANDROID_NATIVE_APP_1_H__

#include "IEcoBase1.h"

/* Android NDK r15 и выше */
#include <android/configuration.h>
#include <android/looper.h>
#include <android/native_activity.h>

/* IEcoAndroidNativeApp1 IID = {41D50AF9-2EED-4355-99E0-C40BC3AFBF43} */
#ifndef __IID_IEcoAndroidNativeApp1
static const UGUID IID_IEcoAndroidNativeApp1 = {0x01, 0x10, {0x41, 0xD5, 0x0A, 0xF9, 0x2E, 0xED, 0x43, 0x55, 0x99, 0xE0, 0xC4, 0x0B, 0xC3, 0xAF, 0xBF, 0x43}};
#endif /* __IID_IEcoAndroidNativeApp1 */

typedef struct IEcoAndroidNativeApp1* IEcoAndroidNativeApp1Ptr_t;

typedef struct IEcoAndroidNativeApp1VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoAndroidNativeApp1Ptr_t me, /* in */ const UGUID* riid, /* out */ void **ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoAndroidNativeApp1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoAndroidNativeApp1Ptr_t me);

    /* IEcoAndroidNativeApp1 */
    int16_t (ECOCALLMETHOD *get_Activity)(/* in */IEcoAndroidNativeApp1Ptr_t me, /* out */ ANativeActivity** activity, /* out */ void** savedState, /* out */ size_t* savedStateSize);
    int16_t (ECOCALLMETHOD *get_Window)(/* in */IEcoAndroidNativeApp1Ptr_t me, /* out */ ANativeWindow** window);

} IEcoAndroidNativeApp1VTbl, *IEcoAndroidNativeApp1VTblPtr;

interface IEcoAndroidNativeApp1 {
    struct IEcoAndroidNativeApp1VTbl *pVTbl;
} IEcoAndroidNativeApp1;

#endif /* __I_ECO_ANDROID_NATIVE_APP_1_H__ */
