# **Writing Custom Plugins & Adapters**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Hexagonal Adapter Pattern**
To build a custom adapter plugin (e.g., a custom vector store or custom linter):

1. **Import Protocol**: Inherit from the target `typing.Protocol` in `sagiha2.kernel.protocols`.
2. **Implement Signature**: Fulfill all required async methods without introducing side effects.
3. **Register Plugin**: Register the implementation class in the Kernel DI container or place it in `src/sagiha2/adapters/`.
