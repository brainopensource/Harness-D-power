# **High-Performance Native Sidecars (Rust & Go)**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Compiled Sidecar Services**
To maintain unblocked responsiveness in the main Python event loop, CPU-heavy tasks run as separate compiled sidecar services communicating over gRPC / Unix domain sockets:

* **`sidecars/ast_indexer_rust/`**: High-speed Rust service using Tree-sitter for multi-language AST parsing, symbol resolution, and scope skeletonization over gRPC.
* **`sidecars/tq_vector_go/`**: Native Go service utilizing `tqdb` for zero-copy memory-mapped 4-bit scalar vector quantization search without decompressing vectors into memory.
