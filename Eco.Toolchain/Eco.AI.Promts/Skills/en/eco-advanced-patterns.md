---
name: Advanced Eco Patterns
description: Advanced design patterns: connection points, aggregation, and containment within the Eco model
version: 1.1.0
---

# SKILL: ADVANCED ECO PATTERNS

## 1. CONNECTION POINTS (Events)
- Implement `IEcoConnectionPointContainer` in the main object.
- Create helper objects: `CEcoConnectionPoint`, `CEcoEnumConnectionPoints`, and `CEcoEnumConnections`.
- Logic: The Sink interface is always passed via `Advise`.

## 2. AGGREGATION (COM Rules)
- **Inner (Aggregatable)**: Implement a Non-delegating Unknown (Non-delegating `IEcoUnknown`) to manage the reference counter. All other interfaces must delegate their calls to `pIUnkOuter`.
- **Outer (Aggregator)**: Pass your own `IEcoUnknown` as `pIUnkOuter` when creating the inner object. Store only a pointer to its `IEcoUnknown`.

## 3. CONTAINMENT
- The outer component fully owns the inner component.
- The outer component implements its own interfaces by internally calling the methods of the inner component.
- **Strict**: The inner `IEcoUnknown` is never exposed directly to the client.
