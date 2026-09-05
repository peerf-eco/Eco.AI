---
name: Advanced Eco Patterns
description: Расширенные шаблоны проектирования: точки подключения, агрегация и включение в модели Eco
version: 1.1.0
---

# SKILL: ADVANCED ECO PATTERNS

## 1. CONNECTION POINTS (Events)
- Реализуй `IEcoConnectionPointContainer` в основном объекте.
- Создай вспомогательные объекты: `CEcoConnectionPoint`, `CEcoEnumConnectionPoints`, `CEcoEnumConnections`.
- Логика: Sink всегда передается через `Advise`.

## 2. AGGREGATION (COM Rules)
- **Inner (Aggregatable)**: Реализуй Неделегируемый Unknown (Non-delegating `IEcoUnknown`) для управления счетчиком. Остальные интерфейсы делегируют вызовы в `pIUnkOuter`.
- **Outer (Aggregator)**: Передавай свой `IEcoUnknown` как `pIUnkOuter` при создании внутреннего объекта. Храни только указатель на его `IEcoUnknown`.

## 3. CONTAINMENT
- Внешний компонент полностью владеет внутренним.
- Внешний компонент реализует свои интерфейсы, вызывая внутри методы внутреннего.
- **Strict**: Внутренний `IEcoUnknown` никогда не отдается клиенту напрямую.
