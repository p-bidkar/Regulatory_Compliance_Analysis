# RegComply: A Multi-Agent AI System for Automated Regulatory Compliance Document Analysis

---

**Student Name:** Prasanna Vinayak Bidkar
**B-Number:** B01090724
**Advisor:** Professor Madden
**Institution:** State University of New York at Binghamton
**Date of Completion:** April 28, 2026
**Report Type:** Progress Report (Project continuation through December 2026)

---

## Abstract

Financial institutions are required to continuously monitor and respond to regulatory updates issued by bodies such as the Securities and Exchange Commission (SEC) and the Financial Industry Regulatory Authority (FINRA). The current process is predominantly manual: compliance teams read hundreds of pages of regulatory text, identify substantive changes, and cross-reference those changes against internal policy documents to determine what must be updated. This process is slow, costly, and error-prone. This project, RegComply, addresses this problem by designing and implementing a multi-agent AI system that automates regulatory compliance document analysis. The system consists of three specialized AI agents coordinated through a LangGraph workflow: Agent 1 detects substantive changes between old and new regulation versions, Agent 2 uses retrieval-augmented generation (RAG) to identify which internal company policy sections are affected, and Agent 3 generates specific, citation-grounded policy update recommendations. The system is built using LlamaIndex for document retrieval, ChromaDB for vector storage, NVIDIA NIM-hosted large language models for analysis and generation, and Streamlit for a working web demonstration. As of April 2026, the full three-agent pipeline is implemented and operational on a realistic dataset comprising one SEC Rule 17a-4 amendment and four company compliance policy documents. The system correctly detects 14 substantive regulatory changes and retrieves relevant policy evidence in under three minutes per regulation. The remaining work through December 2026 focuses on expanding the evaluation corpus, implementing formal accuracy metrics, and producing the final technical report.

---

## 1. Introduction and Motivation

### 1.1 The Problem

Financial services companies operate under a dense and constantly evolving regulatory environment. The SEC, FINRA, FinCEN, and other regulatory bodies regularly issue new rules, amendments, and guidance that require institutions to update their internal compliance policies. A single regulatory amendment can run to dozens of pages and affect multiple distinct internal policy documents simultaneously.

The current compliance workflow is overwhelmingly manual. A typical compliance team must read the full text of a new regulation, identify every section that differs from the prior version, and then search through hundreds of pages of internal policies to find every clause that requires revision. According to industry estimates, this process takes several weeks per major regulation and costs institutions over $300,000 annually in staff time alone. The consequences of missing a required update are severe: regulatory fines ranging from hundreds of thousands to hundreds of millions of dollars, reputational damage, and in some cases criminal liability for firm officers.

### 1.2 Opportunity

Recent advances in large language models (LLMs) and retrieval-augmented generation (RAG) create a genuine opportunity to automate significant portions of this workflow. LLMs can be prompted to compare legal text and identify substantive differences. RAG systems can efficiently retrieve the most semantically relevant sections from a large policy corpus. Multi-agent orchestration frameworks allow these capabilities to be composed into a reliable, auditable pipeline.

The global RegTech market was valued at $14.8 billion in 2024 and is growing rapidly, driven by increasing regulatory complexity and institutional demand for automation. This project targets a concrete, high-value slice of that market: the compliance document analysis workflow.

### 1.3 Project Goals

The primary goals of this project are:

1. Build a working multi-agent system that automates the regulatory change detection, policy retrieval, and recommendation generation workflow.
2. Evaluate the system on 5 to 10 historical SEC and FINRA regulatory amendments with documented performance metrics targeting greater than 80% retrieval accuracy, greater than 90% citation accuracy, and less than 5 minutes processing time per regulation.
3. Demonstrate the system through a web interface suitable for a compliance team user.
4. Produce a technical report covering system architecture, RAG optimization techniques, multi-agent coordination patterns, and a comprehensive evaluation with failure mode analysis.

---

## 2. Background and Related Work

### 2.1 Regulatory Compliance and NLP

Prior work on NLP for legal and regulatory text has largely focused on named entity recognition, clause extraction, and contract review. Systems such as LexNLP and various transformer-based contract analysis tools have demonstrated that LLMs can parse and reason over legal language with meaningful accuracy. However, the specific problem of cross-referencing regulatory changes against internal policy documents and generating actionable remediation recommendations remains largely unaddressed in the academic literature. This project contributes to that gap.

### 2.2 Retrieval-Augmented Generation

RAG was introduced as a technique to ground LLM outputs in retrieved evidence, reducing hallucination and enabling accurate citation. For long legal documents, effective RAG requires careful attention to chunking strategy, embedding model selection, and retrieval depth. Prior work has shown that section-aware chunking (splitting by logical document structure rather than fixed character counts) significantly improves retrieval precision on legal text. This project implements a paragraph-boundary chunker with configurable overlap to preserve cross-sentence context at chunk boundaries.

### 2.3 Multi-Agent Systems

Multi-agent frameworks allow complex tasks to be decomposed into specialized sub-agents that operate sequentially or in parallel. LangGraph provides a directed graph abstraction over LangChain primitives, with optional support for conditional branching, human-in-the-loop hooks, and checkpointing. The current RegComply implementation uses LangGraph as a linear three-node pipeline with shared PipelineState; branching, human-in-the-loop review, and checkpointing are planned for later work rather than present in the current code.

### 2.4 Evaluation Challenges

Evaluating compliance AI systems is non-trivial because ground truth requires legal domain expertise. This project will construct a small labeled evaluation set by manually annotating which policy chunks are affected by each regulatory change and which specific policy clauses require revision. Retrieval accuracy will be measured as recall at k on this labeled set. Citation accuracy will be measured as the fraction of generated recommendations that contain a verbatim policy excerpt verifiably present in the retrieved chunk used to generate that recommendation.

---

## 3. System Architecture

### 3.1 Overview

RegComply is a Python package built with a src-layout under the package name regcomply. The system consists of five functional layers: data ingestion and normalization, text chunking and indexing, LLM inference, multi-agent orchestration, and user interface.

### 3.2 Data Pipeline

Raw regulatory and policy documents are stored as plain text files under data/raw/. The ingest layer normalizes whitespace and removes trailing artifacts. The chunking layer splits normalized text at paragraph boundaries, accumulates paragraphs into chunks not exceeding 1,500 characters, and carries a 150-character overlap into the start of each subsequent chunk to preserve cross-boundary context. Each chunk is assigned a stable identifier, a section path, and a source document ID, which are stored as metadata in the vector index. Rebuilding the policy index replaces the existing ChromaDB collection so duplicate chunks are not accumulated across runs.

Policy documents are embedded using sentence-transformers/all-MiniLM-L6-v2, a 22-million-parameter bi-encoder model that runs locally without any API dependency. Embeddings are stored in a persistent ChromaDB collection on disk using the LlamaIndex vector store abstraction. This design ensures that potentially sensitive policy text is never transmitted to an external service during the retrieval phase.

### 3.3 Agent 1: Change Detection

Agent 1 receives the full text of the baseline and updated regulation versions. It calls the hosted large language model with a structured prompt instructing it to identify every substantive change, defined as a difference that alters a legal obligation, threshold, deadline, definition, or scope. Typographical corrections and formatting differences are explicitly excluded. The agent returns a structured list of change items, each containing the affected section, a change type label (new requirement, modified requirement, deleted requirement, extended deadline, or new definition), a one-sentence summary, the baseline and updated text excerpts, and a compliance impact rating (high, medium, or low).

### 3.4 Agent 2: Policy RAG

Agent 2 takes the change items produced by Agent 1 and constructs a retrieval query for each detected change by concatenating the change summary with the updated regulatory text excerpt (truncated to 300 characters). It executes semantic search against the ChromaDB policy index using the same MiniLM embedding model used during indexing. The top-k results (currently k equals six) are deduplicated by chunk ID and returned as a ranked list with similarity scores.

### 3.5 Agent 3: Recommendations

Agent 3 receives both the change items and the retrieved policy chunks. It calls the LLM with a structured prompt instructing it to produce a JSON array of policy update recommendations, each grounded in a specific retrieved chunk. Each recommendation must include the policy document name, priority level, the regulatory section driving the change, the verbatim current policy text that requires revision, the recommended replacement language, a rationale, and the chunk ID of the supporting evidence. A programmatic citation gate then verifies that the quoted current policy text appears in the referenced chunk after whitespace normalization, marking each citation as verified or unverified.

### 3.6 LLM Adapter

All LLM calls are routed through a single llm.py adapter module that reads endpoint configuration from environment variables (OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL). The adapter uses an OpenAI-compatible HTTP client, which allows the system to target any compliant provider. The current deployment targets NVIDIA NIM hosted models. The adapter strips model-specific reasoning preamble (such as thinking blocks produced by reasoning-mode models) before returning text, ensuring JSON parsing robustness across different model variants.

### 3.7 Orchestration

The three agents are wired as nodes in a LangGraph StateGraph with a shared PipelineState TypedDict. The graph is compiled once per session and cached. Execution flows linearly: change detection, then policy RAG, then recommendations, then END. Each stage records elapsed seconds into the shared timings field. The pipeline is invoked through a single run_pipeline function that accepts an initial state and returns the fully populated output state.

---

## 4. Implementation Progress and Preliminary Results

### 4.1 Corpus

The current evaluation corpus consists of one regulatory amendment pair and four internal policy documents:

**Regulatory pair:** SEC Rule 17a-4 (baseline pre-2026 version versus the March 2026 amendment). The amendment introduces five substantive changes: extension of electronic communications retention from three to five years, new mandatory cloud storage certification requirements (FedRAMP Moderate or equivalent), new geographic separation requirement for duplicate copies (minimum 100 miles), new cybersecurity incident notification obligation (24 hours to the Commission), and a new real-time audit trail requirement effective September 2026.

**Policy corpus:** Records Retention and Management Policy (CMP-001), Anti-Money Laundering and Know Your Customer Policy (CMP-002), Supervisory Procedures and Controls Policy (CMP-005), and Information Security and Data Governance Policy (IT-012). These four synthetic documents total approximately 36 KB of compliance-style policy text (about 490 lines), yielding on the order of 30 indexed chunks after normalization and chunking. Expanding to a larger, page-scale corpus remains planned future work.

### 4.2 Results on Current Corpus

Running the full pipeline against the SEC Rule 17a-4 amendment pair produces the following output:

- **Changes detected:** 14 substantive changes identified by Agent 1 across sections covering effective dates, electronic storage, communications retention, cloud provider requirements, cybersecurity notification, and audit trail obligations.
- **Policy chunks retrieved:** 6 unique chunks ranked by semantic similarity, drawn from the Records Retention Policy and Data Governance Policy, which are the two documents most directly affected by this amendment.
- **Recommendations generated:** Structured recommendations produced with supporting chunk IDs and citation verification status.
- **End-to-end latency:** Approximately 60 to 90 seconds using the reasoning-class model (nvidia/nemotron-3-nano-omni-30b-a3b-reasoning) and approximately 20 to 40 seconds using a lightweight instruction model (meta/llama-3.1-8b-instruct).

### 4.3 Demonstration

The system is deployed as a Streamlit web application. A user selects the baseline and updated regulation files from a sidebar dropdown, clicks Run analysis, and receives results in four tabs: detected changes with baseline and updated text comparison, retrieved policy chunks with similarity scores, structured recommendations with priority and regulatory citation, and a citation verification panel alongside the raw JSON pipeline output.

---

## 5. Remaining Work and Timeline (May to December 2026)

### May to June 2026: Evaluation corpus expansion and labeled dataset

Expand the regulatory test set from one to five to ten historical SEC and FINRA amendment pairs. Construct a manually annotated gold label set specifying which policy chunks are ground-truth relevant for each regulatory change. Implement the formal evaluation harness (src/regcomply/eval/) to compute recall at k, citation accuracy, and end-to-end latency across all test cases.

### July to August 2026: RAG optimization and mid-year checkpoint

Experiment with hybrid retrieval (BM25 plus dense vector search) to improve recall on acronym-heavy regulatory text. Evaluate cross-encoder reranking as a post-retrieval step. Conduct model ablation study comparing the reasoning-class model against lightweight instruction models on the labeled evaluation set. Produce a working demo snapshot for mid-year checkpoint meeting.

### September to October 2026: Failure mode analysis and system hardening

Analyze cases where the system fails to retrieve the correct policy section or produces unverified citations. Document the failure taxonomy. Add a human-review flag in the Streamlit interface for low-confidence outputs. Improve the citation gate to handle paraphrased rather than verbatim policy text.

### November to December 2026: Final report and presentation

Write the eight-page final technical report covering system architecture, RAG optimization results, multi-agent coordination patterns, full evaluation results, and failure mode analysis. Prepare the live demonstration for the presentation, including a real-time processing example and architecture diagrams.

---

## 6. References

1. Lewis, P. et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. Advances in Neural Information Processing Systems.
2. Chase, H. (2022). LangChain: Building applications with LLMs through composability. GitHub repository. https://github.com/langchain-ai/langchain
3. Hong, S. et al. (2023). MetaGPT: Meta Programming for Multi-Agent Collaborative Framework. arXiv preprint.
4. Reimers, N. and Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. Proceedings of EMNLP 2019.
5. NVIDIA Corporation. (2026). Nemotron 3 Nano Omni: Efficient and Open Multimodal Reasoning Model. NVIDIA Research Technical Report.
6. Securities and Exchange Commission. (2026). Amendments to Rule 17a-4 under the Securities Exchange Act of 1934. Release No. 34-97142.
7. Liu, J. (2022). LlamaIndex: A data framework for LLM applications. GitHub repository. https://github.com/run-llama/llama_index
8. Grand View Research. (2024). RegTech Market Size, Share and Trends Analysis Report. Market research report.
