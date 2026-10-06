---
name: fastapi-architecture
description: Architecture rules and layer separation for FastAPI backend.
---

# FastAPI Architecture

## Strict Layering
This project enforces a strict 3-tier architecture. Do not bleed logic between layers.

### 1. Routes (`core/routes/`)
- Purely for HTTP request parsing and response formatting.
- NO BUSINESS LOGIC.
- Inject dependencies (Services) via FastAPI `Depends()`.

### 2. Services (`core/services/`)
- Contains all business logic (e.g., trading algorithms, data aggregation).
- Does not know about HTTP requests or FastAPI routers.
- Calls the Repository layer to fetch/store data.

### 3. Repositories (`core/repositories/`)
- Contains all DuckDB SQL queries and database interactions.
- Returns clean Pydantic models or domain objects, NOT raw database cursors.

## Dependency Injection
Use `Depends()` strictly for database connections and service instantiation in routers.
