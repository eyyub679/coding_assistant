# Coding Assistant Enhancement Ideas

This document outlines potential feature ideas, architectural improvements, and learning topics for the coding assistant project, specifically tailored around the current architecture in `./src/coding_assistant/` (utilizing LangGraph, Tree-sitter AST parsing, Pydantic structured schemas, and developer tools).

## 1. LangGraph & Agent Architecture Improvements
- **Advanced State Management & Checkpointing**: Extend `get_agent()` in `src/coding_assistant/agent.py` with persistent checkpointer storage (e.g., using SQLite or Postgres via LangGraph checkpointers) so agent sessions can be paused, resumed, and inspected across runs.
- **Hierarchical Multi-Agent Systems**: Split the monolithic agent graph into specialized sub-agents managed by a supervisor or planner node (enhancing `planner_node` and `PlannerOutput` in `schemas.py` into a *Research Agent*, a *Code Writer Agent*, a *Test & Verification Agent*, and a *Refactoring Agent*).
- **Human-in-the-Loop Refinements**: Enhance `human_intervention_node` in `src/coding_assistant/agent.py` (which currently tracks `error_count` and requests intervention) with rich CLI prompts, approval gates for destructive tool calls (`write_file`, `edit_file`, `run_command` in `tools.py`), or a dedicated web UI.
- **Dynamic Subgraphs & Reflection Loops**: Add a self-correction/reflection loop where the agent reviews test failures or linter errors from `run_command` and iteratively fixes its own code (leveraging `should_continue` conditional routing and error state counters).

## 2. Tree-sitter & Code Understanding Enhancements
- **Multi-File Semantic Search / Call Graphs**: Expand `src/coding_assistant/ast_extractor.py` (which currently uses `tree-sitter-python`, `tree-sitter-typescript`, `tree-sitter-javascript`, and `tree-sitter-cpp`) to build a repository-wide function call graph, symbol table, and dependency map.
- **Incremental Parsing & Diagnostics**: Leverage Tree-sitter's fast incremental parsing within `tools.py` to check syntax validity of code snippets *before* writing or editing files.
- **Smart Code Slicing**: Instead of sending entire large files or raw full codebase summaries (`codebase_summarizer_node`), use Tree-sitter AST queries to extract only relevant classes, functions, or imports requested by the user or identified via semantic relevance.
- **Support Additional Languages**: Expand language support beyond Python, JS, TS, and C++ (configured in `pyproject.toml` and `ast_extractor.py`) to include Rust, Go, Java, or Ruby using their respective Tree-sitter grammars.

## 3. Tooling & Developer Experience (DevEx)
- **RAG & Vector Search Integration**: Integrate a local vector database (like Chroma or FAISS) with embeddings over the codebase for lightning-fast semantic retrieval of relevant code segments, complementing `codebase_summarizer_node`.
- **Interactive CLI / TUI (Text User Interface)**: Build a rich terminal UI using libraries like `Textual` or `Rich` to visualize the agent's graph state, step progression (`current_step_idx` and `steps` in `State`), token usage, tool execution logs, and step-by-step reasoning in real time.
- **AST-Aware Editing Tools**: Move beyond simple string replacement (`old_string` / `new_string` in `edit_file` / `EditFileSchema`) to AST-aware code editing tools that perform precise structural modifications (e.g., inserting a method into a specific class node using Tree-sitter).
- **Automated Testing & Coverage Loop**: Add specialized tools to run test suites (pytest, jest, etc.) via `run_command`, parse coverage and test failure outputs, and automatically prompt the agent to write missing unit tests.

## 4. Learning Topics & Concepts to Master
- **Stateful Graph Execution**: Deep understanding of LangGraph channels, reducers (`add_messages` in `State`), message history pruning/summarization (`messages_summary_node` in `agent.py`), and resumable workflows.
- **Advanced AST Manipulation**: Mastering Tree-sitter queries (S-expressions), capture groups, and cursor navigation for program analysis (extending `ast_extractor.py`).
- **LLM Function Calling & Structured Outputs**: Designing robust Pydantic schemas (such as `PlannerOutput`, `WriteFileSchema`, `EditFileSchema`, `RunCommandSchema` in `schemas.py`) for deterministic tool use and planning phases.
- **Robust Error Recovery & Safety**: Implementing timeouts (`run_command` timeout parameter), sandboxed command execution, and prompt injection defenses for autonomous agent environments.

## 5. Security, Sandboxing & Cost Optimization
- **Secure Sandboxed Execution**: Run all shell commands (`run_command` via `subprocess.run` in `tools.py`) and generated code snippets in isolated containers (e.g., Docker or Firecracker microVMs) to prevent host system compromise.
- **Token Usage & Cost Tracking**: Implement middleware or callback handlers in `utils.py` (`get_llm()`) to track token consumption per agent step, session, and tool call, setting budget limits to prevent runaway loops.
- **Static Analysis Security Testing (SAST)**: Automatically run security linters (like `bandit` or `semgrep`) on modified code before finalizing file writes.
