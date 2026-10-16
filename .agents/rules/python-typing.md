# Python Code Rules

1. **Strict Typing:** All function signatures MUST have Python type hints. Use `typing.List`, `typing.Dict`, `typing.Optional`, and `typing.Union`.
2. **Docstrings:** All public functions, classes, and modules MUST include Google-style docstrings explaining parameters, return types, and exceptions raised.
3. **Async IO:** Any network I/O or database access that supports `async` must use `async/await` syntax. However, since DuckDB's Python client is primarily synchronous, use thread pools (`run_in_threadpool` from FastAPI) if a query is long-running and blocking the event loop.
4. **Pydantic Validation:** All data entering or leaving the API must be validated using Pydantic models. Do not return raw dictionaries from API endpoints.
