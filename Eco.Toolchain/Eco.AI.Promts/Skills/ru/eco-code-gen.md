---
name: Eco Project Generation Skills
description: Навыки и сценарии генерации исходного кода и компонентов в модели Eco
version: 1.0.0
---

# SKILL: ECO PROJECT GENERATION
При создании проекта компонента следуй строгому порядку:
1. **IDL First**: Всегда начинай с описания интерфейсов в `.idl`.
2. **Factory Single**: Создавай ровно одну фабрику (`CEco...Factory`), реализующую `IEcoComponentFactory`.
3. **Multi-Interface**: Один компонент может реализовать N интерфейсов через одну или несколько VTbl.
4. **Default**: По умолчанию создавай "Stand-alone" компонент.

# SKILL: ECO GENERATION SCENARIOS
На основе ключевых слов в запросе выполняй:
- **"Интерфейс"**: Генерируй структуру VTbl или abstract class.
- **"ID/CID/IID"**: Генерируй только блок статических UGUID.
- **"Приложение" (EcoMain)**: Полный цикл: System -> Bus -> Component -> Release.
- **"Тест"**: Генерируй EcoMain с проверкой результатов методов (без assert).
