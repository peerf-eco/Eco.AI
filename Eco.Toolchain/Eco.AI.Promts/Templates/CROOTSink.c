/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   C[!output FIX_PROJECT_NAME]Sink
 * </сводка>
 *
 * <описание>
 *   Данный исходный код описывает реализацию интерфейсов C[!output FIX_PROJECT_NAME]Sink
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#include "C[!output FIX_PROJECT_NAME]Sink.h"
#include "IEcoConnectionPointContainer.h"

/*
 *
 * <сводка>
 *   Функция QueryInterface
 * </сводка>
 *
 * <описание>
 *   Функция
 * </описание>
 *
 */
int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Sink_QueryInterface(/* in */ struct I[!output FIX_PROJECT_NAME]Events* me, /* in */ const UGUID* riid, /* out */ void** ppv) {
    if ( IsEqualUGUID(riid, &IID_I[!output FIX_PROJECT_NAME]Events ) ) {
        *ppv = me;
        me->pVTbl->AddRef(me);
        return 0;
    }
    else if ( IsEqualUGUID(riid, &IID_IEcoUnknown ) ) {
        *ppv = me;
        me->pVTbl->AddRef(me);
        return 0;
    }

    *ppv = 0;

    return -1;
}

/*
 *
 * <сводка>
 *   Функция AddRef
 * </сводка>
 *
 * <описание>
 *   Функция
 * </описание>
 *
 */
uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Sink_AddRef(/* in */ struct I[!output FIX_PROJECT_NAME]Events* me) {
    C[!output FIX_PROJECT_NAME]Sink* pCMe = (C[!output FIX_PROJECT_NAME]Sink*)me;

    if (me == 0 ) {
        return -1;
    }

    pCMe->m_cRef++;
    return pCMe->m_cRef;
}

/*
 *
 * <сводка>
 *   Функция Release
 * </сводка>
 *
 * <описание>
 *   Функция
 * </описание>
 *
 */
uint32_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Sink_Release(/* in */ struct I[!output FIX_PROJECT_NAME]Events* me) {
    C[!output FIX_PROJECT_NAME]Sink* pCMe = (C[!output FIX_PROJECT_NAME]Sink*)me;

    if (me == 0 ) {
        return -1;
    }

    /* Уменьшение счетчика ссылок на компонент */
    --pCMe->m_cRef;

    /* В случае обнуления счетчика, освобождение данных экземпляра */
    if ( pCMe->m_cRef == 0 ) {
        deleteC[!output FIX_PROJECT_NAME]Sink((I[!output FIX_PROJECT_NAME]Events*)pCMe);
        return 0;
    }
    return pCMe->m_cRef;
}

/*
 *
 * <сводка>
 *   Функция OnMyCallback
 * </сводка>
 *
 * <описание>
 *   Функция обратного вызова
 * </описание>
 *
 */
int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Sink_OnMyCallback(/* in */ struct I[!output FIX_PROJECT_NAME]Events* me, /* in */ char_t* Name) {
    C[!output FIX_PROJECT_NAME]Sink* pCMe = (C[!output FIX_PROJECT_NAME]Sink*)me;

    if (me == 0 ) {
        return -1;
    }


    return 0;
}


/*
 *
 * <сводка>
 *   Функция Advise
 * </сводка>
 *
 * <описание>
 *   Функция
 * </описание>
 *
 */
int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Sink_Advise(/* in */ struct C[!output FIX_PROJECT_NAME]Sink* me, /* in */I[!output FIX_PROJECT_NAME] *pI[!output FIX_PROJECT_NAME]) {
    IEcoConnectionPointContainer* pCPC = 0;
    IEcoConnectionPoint* pCP = 0;
    int16_t result = 0;

    result = pI[!output FIX_PROJECT_NAME]->pVTbl->QueryInterface(pI[!output FIX_PROJECT_NAME], &IID_IEcoConnectionPointContainer, (void**)&pCPC);

    if (result == 0 && pCPC != 0) {
        result = pCPC->pVTbl->FindConnectionPoint(pCPC, &IID_I[!output FIX_PROJECT_NAME]Events, &pCP);
        pCPC->pVTbl->Release(pCPC);
        pCPC = 0;
        if (result == 0 && pCP != 0) {

            result = pCP->pVTbl->Advise(pCP, (IEcoUnknown*)me, &me->m_cCookie);
            pCP->pVTbl->Release(pCP);
            pCP = 0;
        }
    }

    return result;
}

/*
 *
 * <сводка>
 *   Функция Unadvise
 * </сводка>
 *
 * <описание>
 *   Функция
 * </описание>
 *
 */
int16_t ECOCALLMETHOD C[!output FIX_PROJECT_NAME]Sink_Unadvise(/* in */ struct C[!output FIX_PROJECT_NAME]Sink* me, /* in */I[!output FIX_PROJECT_NAME] *pI[!output FIX_PROJECT_NAME]) {
    IEcoConnectionPointContainer* pCPC = 0;
    IEcoConnectionPoint * pCP = 0;
    int16_t result = 0;

    if (me->m_cCookie) {
        result = pI[!output FIX_PROJECT_NAME]->pVTbl->QueryInterface(pI[!output FIX_PROJECT_NAME], &IID_IEcoConnectionPointContainer, (void**)&pCPC);
        if (result == 0) {
            result = pCPC->pVTbl->FindConnectionPoint(pCPC, &IID_I[!output FIX_PROJECT_NAME]Events, &pCP);
            pCPC->pVTbl->Release(pCPC);
            pCPC = 0;
            if (result == 0) {
                result = pCP->pVTbl->Unadvise(pCP, me->m_cCookie);
                pCP->pVTbl->Release(pCP);
                pCP = 0;
            }
        }
    }
    return result;
}

/* Create Virtual Table I[!output FIX_PROJECT_NAME]VTblEvents */
I[!output FIX_PROJECT_NAME]VTblEvents g_x[!output GUID_IID_TARGET]VTblEvents = {
    C[!output FIX_PROJECT_NAME]Sink_QueryInterface,
    C[!output FIX_PROJECT_NAME]Sink_AddRef,
    C[!output FIX_PROJECT_NAME]Sink_Release,
    C[!output FIX_PROJECT_NAME]Sink_OnMyCallback
};

/*
 *
 * <сводка>
 *   Функция Create
 * </сводка>
 *
 * <описание>
 *   Функция создания экземпляра
 * </описание>
 *
 */
int16_t ECOCALLMETHOD createC[!output FIX_PROJECT_NAME]Sink(/* in */ IEcoMemoryAllocator1* pIMem, /* out */ I[!output FIX_PROJECT_NAME]Events** ppI[!output FIX_PROJECT_NAME]Events) {
    int16_t result = -1;
    C[!output FIX_PROJECT_NAME]Sink* pCMe = 0;

    /* Проверка указателей */
    if (ppI[!output FIX_PROJECT_NAME]Events == 0 || pIMem == 0 ) {
        return result;
    }

    /* Выделение памяти для данных экземпляра */
    pCMe = (C[!output FIX_PROJECT_NAME]Sink*)pIMem->pVTbl->Alloc(pIMem, sizeof(C[!output FIX_PROJECT_NAME]Sink));

    /* Сохранение указателя на интерфейс для работы с памятью */
    pCMe->m_pIMem = pIMem;
    pCMe->m_pIMem->pVTbl->AddRef(pCMe->m_pIMem);

    /* Установка счетчика ссылок на компонент */
    pCMe->m_cRef = 1;

    /* Создание таблицы функций интерфейса IEcoP2PEvents */
    pCMe->m_pVTblI[!output FIX_PROJECT_NAME]Events = &g_x[!output GUID_IID_TARGET]VTblEvents;

    *ppI[!output FIX_PROJECT_NAME]Events = (I[!output FIX_PROJECT_NAME]Events*)pCMe;

    return 0;
};

/*
 *
 * <сводка>
 *   Функция Delete
 * </сводка>
 *
 * <описание>
 *   Функция освобождения экземпляра
 * </описание>
 *
 */
void ECOCALLMETHOD deleteC[!output FIX_PROJECT_NAME]Sink(I[!output FIX_PROJECT_NAME]Events* pI[!output FIX_PROJECT_NAME]Events) {
    C[!output FIX_PROJECT_NAME]Sink* pCMe = (C[!output FIX_PROJECT_NAME]Sink*)pI[!output FIX_PROJECT_NAME]Events;
    IEcoMemoryAllocator1* pIMem = 0;

    if (pI[!output FIX_PROJECT_NAME]Events != 0 ) {
        pIMem = pCMe->m_pIMem;
        /* Освобождение */
        pIMem->pVTbl->Free(pIMem, pCMe);
        pIMem->pVTbl->Release(pIMem);
    }
};
