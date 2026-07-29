# **Language Server Protocol (`LSPAdapter`) Interface**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Overview**
`LSPAdapter` is a first-class hexagonal port that exposes real-time Language Server Protocol capabilities directly to agents for type checking, syntax diagnostics, and definition lookups:

```python
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

@runtime_checkable
class LSPAdapter(Protocol):
    async def get_diagnostics(self, file_path: str) -> List[DiagnosticItem]: ...
    async def get_definition(self, file_path: str, line: int, column: int) -> Optional[Dict[str, Any]]: ...
    async def get_references(self, file_path: str, line: int, column: int) -> List[Dict[str, Any]]: ...
```
