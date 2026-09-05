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
 *   Данный заголовок описывает реализацию компонента C[!output FIX_PROJECT_NAME]Sink
 * </описание>
 *
 * <автор>
 *   Copyright (c) 2016 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __C_[!output UPPER_PROJECT_NAME]_SINK_H__
#define __C_[!output UPPER_PROJECT_NAME]_SINK_H__

#include "I[!output FIX_PROJECT_NAME].h"
#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"

typedef struct C[!output FIX_PROJECT_NAME]Sink {

    /* Таблица функций интерфейса I[!output FIX_PROJECT_NAME]Events */
    I[!output FIX_PROJECT_NAME]VTblEvents* m_pVTblI[!output FIX_PROJECT_NAME]Events;

    /* Вспомогательные функции */
    int16_t (ECOCALLMETHOD *Advise)(/* in */ struct C[!output FIX_PROJECT_NAME]Sink* me, /* in */I[!output FIX_PROJECT_NAME] *pI[!output FIX_PROJECT_NAME]);
    int16_t (ECOCALLMETHOD *Unadvise)(/* in */ struct C[!output FIX_PROJECT_NAME]Sink* me, /* in */I[!output FIX_PROJECT_NAME] *pI[!output FIX_PROJECT_NAME]);

    /* Счетчик ссылок */
    uint32_t m_cRef;
    uint32_t m_cCookie;

    /* Интерфейс для работы с памятью */
    IEcoMemoryAllocator1* m_pIMem;


} C[!output FIX_PROJECT_NAME]Sink, *C[!output FIX_PROJECT_NAME]SinkPtr;

/* Создание экземпляра */
int16_t ECOCALLMETHOD createC[!output FIX_PROJECT_NAME]Sink(/* in */ IEcoMemoryAllocator1* pIMem, /* out */ I[!output FIX_PROJECT_NAME]Events** ppI[!output FIX_PROJECT_NAME]Events);
/* Удаление */
void ECOCALLMETHOD deleteC[!output FIX_PROJECT_NAME]Sink(/* in */ I[!output FIX_PROJECT_NAME]Events* pI[!output FIX_PROJECT_NAME]Events);

#endif /* __C_[!output UPPER_PROJECT_NAME]_SINK_H__ */
