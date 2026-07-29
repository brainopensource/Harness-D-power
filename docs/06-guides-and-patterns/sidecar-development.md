# **High-Performance Sidecar Development (Rust & Go)**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Sidecar Service Architecture**
* **Rust AST Sidecar (`sidecars/ast_indexer_rust/`)**: Build compiled binary exposing gRPC protobuf endpoints for Tree-sitter AST symbol resolution.
* **Go Vector Sidecar (`sidecars/tq_vector_go/`)**: Build compiled binary exposing gRPC protobuf endpoints for `tqdb` memory-mapped vector search.
