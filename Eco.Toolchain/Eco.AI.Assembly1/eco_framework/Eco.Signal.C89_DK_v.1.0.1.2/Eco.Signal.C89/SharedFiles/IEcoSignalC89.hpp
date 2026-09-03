/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoSignalC89
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает интерфейс IEcoSignalC89
 * </описание>
 *
 * <ссылка>
 *
 * </ссылка>
 *
 * <автор>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_SIGNAL_C89_HPP__
#define __I_ECO_SIGNAL_C89_HPP__

#include "IEcoBase1.hpp"

#ifdef ECO_OS
#ifndef __ECO_SIGNAL_H__

/* Signal types */
#define SIGINT          2       /* interrupt */
#define SIGILL          4       /* illegal instruction - invalid function image */
#define SIGFPE          8       /* floating point exception */
#define SIGSEGV         11      /* segment violation */
#define SIGTERM         15      /* Software termination signal from kill */
#define SIGBREAK        21      /* Ctrl-Break sequence */
#define SIGABRT         22      /* abnormal termination triggered by abort call */

/* Signal action codes */
#define SIG_DFL         (void (ECOCDECLMETHOD *)(int))0       /* default signal action */
#define SIG_IGN         (void (ECOCDECLMETHOD *)(int))1       /* ignore signal */

/* Signal error value (returned by signal call on error) */
#define SIG_ERR         (void (ECOCDECLMETHOD *)(int))-1      /* signal error value */

#endif
#endif

/* IEcoSignalC89 IID = {00000000-0000-0000-0000-890000009101} */
#ifndef __IID_IEcoSignalC89
static const UGUID IID_IEcoSignalC89 = {0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x89, 0x00, 0x00, 0x00, 0x91, 0x01}};
#endif /* __IID_IEcoSignalC89 */

interface IEcoSignalC89 : public IEcoUnknown {
public:
    /* IEcoSignalC89 */
    virtual void* ECOCALLMETHOD signal(int sig, void (ECOCDECLMETHOD *func)(int)) = 0;
    virtual int ECOCALLMETHOD raise(/* in */ int sig) = 0;
};

#endif /* __I_ECO_SIGNAL_C89_HPP__ */
