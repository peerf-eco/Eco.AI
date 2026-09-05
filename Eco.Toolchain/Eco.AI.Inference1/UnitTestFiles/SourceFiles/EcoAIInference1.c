/*
 * <character encoding>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </character encoding>
 *
 * <summary>
 *   EcoAIInference1
 * </summary>
 *
 * <description>
 *   This source file is the entry point
 * </description>
 *
 * <author>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </author>
 *
 */


/* Eco OS */
#include "IEcoSystem1.h"
#include "IdEcoMemoryManager1.h"
#include "IdEcoInterfaceBus1.h"
#include "IdEcoFileSystemManagement1.h"
#include "IdEcoAIInference1.h"

/*
 *
 * <summary>
 *   EcoMain Function
 * </summary>
 *
 * <description>
 *   EcoMain function - entry point
 * </description>
 *
 */
int16_t EcoMain(IEcoUnknown* pIUnk) {
    int16_t result = -1;
    /* Pointer to the system interface */
    IEcoSystem1* pISys = 0;
    /* Pointer to the interface for working with the system interface bus */
    IEcoInterfaceBus1* pIBus = 0;
    /* Pointer to the memory management interface */
    IEcoMemoryAllocator1* pIMem = 0;
    char_t* name = 0;

    /* System interface check and creation */
    if (pISys == 0) {
        result = pIUnk->pVTbl->QueryInterface(pIUnk, &GID_IEcoSystem, (void **)&pISys);
        if (result != 0 && pISys == 0) {
        /* Free the system interface in case of an error */
            goto Release;
        }
    }

    /* Getting the interface for working with the interface bus */
    result = pISys->pVTbl->QueryInterface(pISys, &IID_IEcoInterfaceBus1, (void **)&pIBus);
    if (result != 0 || pIBus == 0) {
        /* Free in case of an error */
        goto Release;
    }
    /* Getting the memory management interface */
    result = pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoMemoryManager1, 0, &IID_IEcoMemoryAllocator1, (void**) &pIMem);

    /* Check */
    if (result != 0 || pIMem == 0) {
        /* Free the system interface in case of an error */
        goto Release;
    }

    /* Memory block allocation */
    name = (char_t *)pIMem->pVTbl->Alloc(pIMem, 10);

    /* Fill the memory block */
    pIMem->pVTbl->Fill(pIMem, name, 'a', 9);

    printf("hello\n");

    /* Free the memory block */
    pIMem->pVTbl->Free(pIMem, name);

Release:

    /* Free the interface for working with the interface bus */
    if (pIBus != 0) {
        pIBus->pVTbl->Release(pIBus);
    }

    /* Free the memory management interface */
    if (pIMem != 0) {
        pIMem->pVTbl->Release(pIMem);
    }


    /* Free the system interface */
    if (pISys != 0) {
        pISys->pVTbl->Release(pISys);
    }

    return result;
}


void Test_Inference_Full_Run(IEcoInterfaceBus1* pIBus) {
    IEcoAIInference1* pIInf = 0;
    IEcoAIModel1* pIModel = 0;
    //IEcoList1* pInTensors = 0;
    //IEcoAITensor1* pIInpTensor = 0;
    //IEcoMatrix1* pIMat = 0;
    float_t val = 0.5f;

    /* 1. Создаем компоненты через шину */
    pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoAIInference1, 0, &IID_IEcoAIInference1, (void**)&pIInf);

    /* 2. Загружаем модель (внутри создается граф с тензорами и операциями) */
    pIInf->pVTbl->Load(pIInf, "model.mpk");

    /* 3. Инициализируем движок моделью */
    pIInf->pVTbl->Init(pIInf, pIModel);

    /* 4. Устанавливаем входные данные */
    //pIModel->pVTbl->get_Inputs(pIModel, &pInTensors);
    //pIInpTensor = (IEcoAITensor1*)pInTensors->pVTbl->Item(pInTensors, 0);
   //// pIInpTensor->pVTbl->get_Matrix(pIInpTensor, &pIMat);
   // pIMat->pVTbl->Fill(pIMat, &val); // Заполняем матрицу входа значениями 0.5

    /* 5. Выполняем ВЕСЬ граф одним вызовом */
    printf("Starting full inference...\n");
    if (pIInf->pVTbl->Run(pIInf) == 0) {
        printf("Inference completed successfully!\n");
        /* Здесь можно извлечь результат через get_Outputs */
    }

    /* Освобождение */
    pIInf->pVTbl->Release(pIInf);
    pIModel->pVTbl->Release(pIModel);
}


void Test_Inference_Step_Debug(IEcoInterfaceBus1* pIBus) {
    IEcoAIInference1* pIInf = 0;
    IEcoAIModel1* pIModel = 0;
//    IEcoGraph1Node* pICurrentNode = 0;
    int16_t status = 0;

    pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoAIInference1, 0, &IID_IEcoAIInference1, (void**)&pIInf);
    
    pIInf->pVTbl->Load(pIInf, "debug_model.mpk");
    pIInf->pVTbl->Init(pIInf, pIModel);

    printf("Starting debug step-by-step mode:\n");

    /* Цикл пошагового выполнения */
    //while (pIInf->pVTbl->Step(pIInf, &pICurrentNode) == 0) {
    //    char_t* nodeName = pICurrentNode->pVTbl->get_Name(pICurrentNode);
    //    
    //    /* Извлекаем данные операции, чтобы понять, что произошло */
    //    IEcoAIOperation1* pIOp = (IEcoAIOperation1*)pICurrentNode->pVTbl->get_Data(pICurrentNode);
    //    
    //    printf("Executed Node: %s\n", nodeName);

    //    /* Инспекция: берем первый выходной тензор этого узла */
    //    IEcoList1* pOutEdges = pICurrentNode->pVTbl->get_TargetEdges(pICurrentNode);
    //    if (pOutEdges->pVTbl->Count(pOutEdges) > 0) {
    //        IEcoGraph1Edge* pEdge = (IEcoGraph1Edge*)pOutEdges->pVTbl->Item(pOutEdges, 0);
    //        IEcoAITensor1* pTensor = (IEcoAITensor1*)pEdge->pVTbl->get_Data(pEdge);
    //        
    //        /* Здесь можно вызвать методы тензора и вывести значения в лог */
    //        printf("  Intermediate tensor '%s' updated.\n", pTensor->pVTbl->get_Name(pTensor));
    //    }
    //    
    //    /* Можно поставить условие остановки на конкретном узле */
    //    if (strcmp(nodeName, "TargetLayer") == 0) break;
    //}

    printf("Debug session finished.\n");

    pIInf->pVTbl->Release(pIInf);
    pIModel->pVTbl->Release(pIModel);
}
