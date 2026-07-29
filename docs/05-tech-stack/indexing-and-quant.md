# **AST Indexing & TurboQuant Vector Quantization**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Indexing & Search Technologies**
* **Sparse Lexical Search**: BM25 keyword matching via SQLite-FTS5 for exact symbol and function definitions.
* **TurboQuant 4-Bit Quantization**: Data-oblivious online vector quantization using Fast Walsh-Hadamard Transforms (FWHT) and 1-bit QJL residual estimators in LanceDB / `tqdb`.
* **AST Skeletonization**: Tree-sitter parsers strip function bodies to preserve interfaces, attributes, signatures, and docstrings for dynamic token compaction.
