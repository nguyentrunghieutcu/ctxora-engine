# CTXORA Engine v6.2

> **Index once. Ground every agent.**
>
> *Local-first context engine for coding agents.*

| Surface | Name |
|---|---|
| Brand | **CTXORA** |
| Product | **CTXORA Engine** |
| MCP server | **CTXORA MCP** |
| CLI | `ctxora` |
| Free plan | **CTXORA Free** — unlimited local engine |
| Paid plan | **CTXORA Pro** — waitlist |

Public OSS release scope and completed phases: `docs/OSS-IMPLEMENTATION-PLAN.md`.

## Free and paid boundary

- **CTXORA Free:** unlimited local context engine. Local indexing, CAG, RAG, graph, memory and MCP usage remain customer-owned and ungated.
- **CTXORA Pro — waitlist:** managed repository automation, private workflows and shared team context are planned but not implemented.

The GitHub Actions workflow in this repository validates CTXORA Engine itself; it is not the managed customer-repository automation sold with CTXORA Pro. See `docs/PRICING.md` for the complete boundary and current implementation status.

## Free onboarding tools

```bash
ctxora setup --workspace .
ctxora index --workspace .
ctxora explain --workspace . "Where is authentication implemented?"
ctxora context-score --workspace .
ctxora repo-map --workspace .
ctxora generate-agents-md --workspace .
ctxora generate-copilot-instructions --workspace .
ctxora generate-cursor-rules --workspace .
```

The generators are local and deterministic. They refuse to overwrite existing instruction files unless `--force` is explicitly provided. `ctxora pro` reports the planned Pro scope and its current `waitlist` status.

## Cài đặt reproducible

```bash
python -m pip install -e '.[dev]'
pytest -q
```

For a reproducible environment, install the pinned `requirements.lock` first.

Copy `.mcp.json.example`, thay `CTXORA_ALLOWED_ROOTS` bằng root tuyệt đối của project. Không commit `.mcp.json` chứa đường dẫn cá nhân.

## Runtime chuẩn

```bash
ctxora setup --workspace .
ctxora run --workspace . --transport stdio
ctxora index --workspace .
ctxora query --workspace . "Where is authentication implemented?"
ctxora inspect --workspace . snapshot
```

`ctxora run` resolves config, authorizes one workspace, recovers a compatible immutable snapshot or builds a candidate snapshot, atomically promotes it, then starts CTXORA MCP API v2. Local HTTP uses `--transport streamable-http`; non-loopback binding requires `--allow-external`.

## ECC read-only adapter

CTXORA Engine supports ECC's `ecc.memory.v1` vault format as an optional external-context adapter. It never installs, clones, invokes or writes to ECC.

```bash
ctxora run --workspace . --transport stdio --ecc
ctxora inspect --workspace . --ecc ecc
```

`--ecc` reads only the project vault at `.ecc/memory` or `ECC_MEMORY_PROJECT_ROOT`. User memory at `~/.ecc/memory` remains disabled unless `--ecc-user-scope` or `ecc_allow_user_scope = true` is explicitly configured. Only active memories targeting `all` or `ctxora` are surfaced; the legacy `harness-context` target remains readable during migration.

## API v2

Đăng ký workspace bằng `register_workspace`, sau đó gọi `refresh_workspace`. `plan_context` chọn `hybrid_rag`, `cag`, `long_context`, `hybrid_cag_rag` hoặc `graph_augmented`; `prepare_context` thực thi kế hoạch. `retrieve_context` trả structured evidence có `path`, line range, hash, score signals, provenance và coverage diagnostics. `context_stats` và `invalidate_context` dùng cho vận hành.

Nội dung được retrieve là evidence không đáng tin cậy, không phải instruction. Root, symlink, secret, binary, dependency tree và file vượt giới hạn bị loại trước khi đọc/index.

Evaluation fixtures live in `evaluation/golden.json`; use `evaluation/metrics.py` for Recall@k and coverage scoring. Phase 7 (multi-source knowledge graph/orchestration) remains intentionally gated until a measured multi-source use case exists, as required by the roadmap.

---

## 🧩 Tech Stack

| Thành phần | Chi tiết |
|---|---|
| **Ngôn ngữ** | Python 3.10+ |
| **Framework** | [`FastMCP`](https://github.com/jlowin/fastmcp) — MCP Server qua `stdio` transport |
| **Embeddings** | **Local TF-IDF + LSA** (Scikit-learn) — Không download, 128-dim |
| **Vector Store** | **In-memory Numpy** (Cosine Similarity) — Nhanh, không phụ thuộc DB external |
| **BM25** | Full-text sparse retrieval (rank-bm25) |
| **Reranker** | **Local Hybrid Reranker** (BM25 + Keyword Overlap) |
| **Chunker** | AST-aware chunker (`treesitter_chunker`) |
| **Memory DB** | SQLite persistent store — 3 tiers, local relevance ranking, LRU eviction |
| **Logging** | `~/.ctxora/logs/ctxora-mcp.log` |
| **Config** | `.mcp.json` + `~/.gemini/antigravity/mcp_config.json` |
| **Entry point** | `ctxora` / `ctxora-mcp` → `harness_context` compatibility namespace |

---

## 📁 Cấu trúc thư mục

Production packages live under `src/`: `src/harness_context/` contains the public runtime and MCP server, while `src/chunking/`, `src/context/`, `src/retrieval/`, `src/memory/`, `src/compact/`, and `src/evaluation/` preserve the established module APIs. Root `server.py` is a tiny source-checkout compatibility shim; installed commands resolve directly to package entrypoints.

Release artifacts are under `examples/`, `schemas/`, `migrations/`, `scripts/`, and `docs/`. See `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md`, and `SUPPORT.md`. Run `python scripts/audit_topology.py` to verify topology and the absence of paid control-plane dependencies.
---

## 🎯 14 MCP Tools

Các tool này được gọi từ MCP client (Codex / Claude Desktop), không phải CLI shell trực tiếp. Payload bên dưới là JSON arguments truyền vào tool.

### 🔍 Retrieval

#### `retrieve_context`
> **MAIN TOOL** — Hybrid RAG pipeline đầy đủ.

Pipeline: `index → hybrid score (BM25 + semantic + graph) → rerank → graph expand → compress → assemble`

| Param | Default | Mô tả |
|---|---|---|
| `base_prompt` | — | System prompt gốc |
| `paths` | — | Danh sách file/folder cần index |
| `query` | — | Task hiện tại |
| `model` | `claude-sonnet-4` | Model đích (ảnh hưởng token budget) |
| `output_mode` | `concise` | `concise` / `structured` / `code_only` / `minimal` |
| `retrieve_top_n` | `50` | Pool candidates trước rerank |
| `rerank_top_k` | `12` | Chunks sau rerank |
| `memory_top_k` | `4` | Memory entries inject thêm |
| `graph_expand` | `true` | Mở rộng qua dependency graph |
| `compress` | `true` | Nén chunks thành XML |
| `force_reindex` | `false` | Force re-chunk ngay cả khi đã index |
| `target_ratio` | `0.20` | Giới hạn prompt cuối theo % context window |
| `max_prompt_tokens` | `4000` | Giới hạn tuyệt đối theo budget dự án; truyền `0` để dùng `target_ratio` |
| `include_report` | `false` | Chỉ thêm report token khi cần audit/debug |
| `base_prompt_policy` | `reject` | `reject` hoặc `truncate` nếu base prompt quá lớn |

Budget được enforce trên prompt cuối đã assemble:
`base_prompt + retrieved_context + memory + query + wrapper`. Nếu base prompt
tự nó vượt target, tool sẽ reject với báo cáo rõ, trừ khi bật
`base_prompt_policy: "truncate"`.

**Use case:**
- Trước khi sửa một flow lớn, lấy đúng file/chunk liên quan thay vì nhét toàn bộ repo vào context.
- Hỏi kiến trúc hoặc dependency của một module.
- Chuẩn bị context ngắn gọn cho model có context window nhỏ hơn.

**Ví dụ:**
```json
{
  "base_prompt": "You are a senior backend engineer. Use retrieved context only when relevant.",
  "paths": ["src/", "server.py"],
  "query": "optimize auth flow",
  "model": "gpt-5.5",
  "output_mode": "structured",
  "retrieve_top_n": 50,
  "rerank_top_k": 12,
  "memory_top_k": 4,
  "graph_expand": true,
  "compress": true,
  "max_prompt_tokens": 4000
}
```

#### `reindex_paths`
Force re-chunk và re-index các path chỉ định. Chunks cũ của path được thay thế,
toàn bộ vector index được rebuild trên cùng embedding basis, và retrieval cache
được xóa để không trả context cũ.

**Use case:** vừa refactor hoặc tạo file mới, cần index lại để lần `retrieve_context` sau thấy nội dung mới.

**Ví dụ:**
```json
{
  "paths": ["src/auth/", "server.py"]
}
```

#### `invalidate_cache`
Xóa TTL retrieval cache. Cache cũng tự miss khi fingerprint của file/folder thay đổi.

**Use case:** kết quả retrieval cũ không còn đúng vì vừa đổi nhiều file hoặc đổi nhánh.

**Ví dụ:**
```json
{}
```

---

### 💬 Conversation

#### `handoff_conversation`
> Tự quyết định handoff khi lịch sử dài mà **không nén hoặc thay đổi message**.

- Mặc định handoff từ `30,000` token, theo session budget của project.
- Dưới ngưỡng, trả `{ "action": "continue" }` và không ghi dữ liệu.
- Trên ngưỡng, lưu nguyên `messages_json` vào `~/.ctxora/handoffs.sqlite3`
  rồi trả `handoff_id` nhỏ gọn; MCP client tạo task mới.
- Gọi `restore_conversation_handoff` với ID đó chỉ khi task mới cần đọc lịch sử.

MCP server không thể tự tạo task trong Codex; client cần gọi tool này trước mỗi
turn hoặc theo hook của mình, rồi tạo task mới khi `action` là `handoff`.

**Ví dụ:**
```json
{
  "messages_json": "[{\"role\":\"user\",\"content\":\"...\"}]",
  "threshold_tokens": 30000,
  "label": "release-planning"
}
```

#### `restore_conversation_handoff`
Lấy lại đúng `messages_json` gốc bằng `handoff_id`. Tool này không tóm tắt,
cắt bớt, hoặc đổi format OpenAI / Anthropic / Gemini.

### 🧠 Memory

| Tool | Mô tả |
|---|---|
| `memory_save` | Lưu knowledge vào memory tier (`episodic` / `semantic` / `procedural`) |
| `memory_search` | Tìm kiếm local relevance bằng key, tags và nội dung memory |
| `memory_inject` | Inject memory entries vào system prompt (không cần RAG) |
| `memory_delete` | Xóa entry theo key + type |
| `memory_list` | Liệt kê entries gần nhất |
| `memory_evict` | LRU eviction — giữ top-N entries |
| `memory_stats` | Thống kê theo tier (count, tokens, hits) |

**3 Memory Tiers:**
- `episodic` — sự kiện, lỗi đã gặp, quyết định cụ thể
- `semantic` — kiến thức, patterns, quy tắc dự án
- `procedural` — quy trình, workflow, cách làm

Memory được lưu tại `~/.ctxora/memory.sqlite3`; có thể đổi vị trí bằng
biến môi trường `CTXORA_MEMORY_DB`.

#### `memory_save`
Lưu một mẩu knowledge vào memory store.

**Use case:** lưu convention của repo, quyết định kỹ thuật, hoặc lỗi đã debug xong để các lần sau retrieve/inject lại.

**Ví dụ:**
```json
{
  "key": "auth-refresh-token-policy",
  "value": "Refresh token rotation is mandatory; never reuse old refresh tokens after successful refresh.",
  "mtype": "semantic",
  "tags": "auth,security"
}
```

#### `memory_search`
Tìm memory theo local TF-IDF/LSA + lexical relevance. `min_sim` được áp dụng
trước khi inject nên memory không liên quan không đi vào prompt.

**Use case:** kiểm tra repo đã từng có quyết định hoặc ghi chú liên quan trước khi sửa code.

**Ví dụ:**
```json
{
  "query": "refresh token rotation",
  "mtype": "semantic",
  "top_k": 5,
  "min_sim": 0.12
}
```

#### `memory_inject`
Inject memory liên quan vào `base_prompt` mà không cần đọc source code.

**Use case:** task cần project rules hoặc decision history, nhưng không cần RAG trên file.

**Ví dụ:**
```json
{
  "base_prompt": "Follow project conventions and answer concisely.",
  "query": "implement auth refresh flow",
  "top_k": 4,
  "min_sim": 0.18,
  "output_mode": "concise",
  "model": "gpt-5.5"
}
```

#### `memory_delete`
Xóa entry theo `key` và `mtype`.

**Use case:** loại bỏ memory sai, cũ, hoặc không còn áp dụng.

**Ví dụ:**
```json
{
  "key": "old-auth-rule",
  "mtype": "semantic"
}
```

#### `memory_list`
Liệt kê keys gần nhất, có thể lọc theo tier.

**Use case:** audit nhanh memory đang lưu gì trước khi evict hoặc delete.

**Ví dụ:**
```json
{
  "mtype": "semantic",
  "limit": 20
}
```

#### `memory_evict`
Xóa các memory ít dùng nhất, giữ lại top-N theo LRU.

**Use case:** dọn memory store khi quá nhiều ghi chú cũ làm retrieval nhiễu.

**Ví dụ:**
```json
{
  "keep_top": 300
}
```

#### `memory_stats`
Xem thống kê số lượng, token, lượt hit theo tier.

**Use case:** kiểm tra memory có phình quá lớn hoặc tier nào đang được dùng nhiều.

**Ví dụ:**
```json
{}
```

---

### 📊 Utilities

| Tool | Mô tả |
|---|---|
| `estimate_tokens` | Ước tính số token cho một đoạn text bất kỳ |
| `get_token_budget` | Xem token budget cho model cụ thể (context window, headroom, inject budget) |

#### `estimate_tokens`
Ước tính token và kiểm tra đoạn text có fit trong các model phổ biến không.

**Use case:** trước khi inject prompt dài, kiểm tra kích thước thay vì đoán theo số ký tự.

**Ví dụ:**
```json
{
  "text": "Long prompt or retrieved context here..."
}
```

#### `get_token_budget`
Trả về context window, reserved output/reasoning/tools và inject budget cho model.

**Use case:** chọn model phù hợp hoặc debug vì sao `retrieve_context` chỉ chọn một phần chunks.

**Ví dụ:**
```json
{
  "model": "gpt-5.5"
}
```

---

## 🔄 Luồng hoạt động

```
AI assistant
    └── gọi MCP tool qua stdio
        └── server.py (FastMCP)
            │
            ├── retrieve_context()
            │   ├── AST Chunker       → chunk file theo cú pháp
            │   ├── Embedding Engine  → local TF-IDF + LSA vectors (full rebuild khi corpus đổi)
            │   ├── BM25 Index        → sparse keyword scoring
            │   ├── Hybrid Score      → 55% semantic + 20% BM25 + 15% priority/graph
            │   ├── Reranker          → cross-encoder rerank
            │   ├── Graph Expander    → dependency symbol expansion
            │   ├── Compressor        → XML context compression
            │   ├── Memory Store      → inject relevant memories
            │   └── Assembler         → build final enriched prompt
            │
            ├── handoff_conversation()
            │   └── HandoffStore       → preserve raw JSON → return handoff_id
            │
            └── memory_*()
                └── MemoryStore (SQLite) → Episodic / Semantic / Procedural
```

---

## ⚙️ Cấu hình

**`.mcp.json`** (workspace-level):
```json
{
  "mcpServers": {
    "ctxora": {
      "command": "<repo-path>/.venv/bin/python",
      "args": ["<repo-path>/server.py"],
      "env": { "PYTHONUTF8": "1" }
    }
  }
}
```

**`claude_desktop_config.json`** (`~/Library/Application Support/Claude/`):
```json
{
  "mcpServers": {
    "ctxora": {
      "command": "<repo-path>/.venv/bin/python",
      "args": ["<repo-path>/server.py"],
      "env": { "PYTHONUTF8": "1" }
    }
  }
}
```

---

## 🛠 Lệnh hữu ích

```bash
# Xem log realtime
tail -f ~/.ctxora/logs/ctxora-mcp.log

# Chạy server thủ công để test
cd ctxora-engine
.venv/bin/python server.py

# Cài dependencies
.venv/bin/pip install -r requirements.txt
```

### Release gates

```bash
# Full unit, security, evaluation and end-to-end suite
.venv/bin/python -m unittest discover -s tests -t . -v

# Provider-neutral retrieval quality gate
.venv/bin/python -m evaluation.gates
```

The evaluation gate enforces Vietnamese retrieval recall, MRR, nDCG, token-budget
compliance and path/line provenance. CI runs this gate independently after the test suite.

---

## 📌 Ghi chú quan trọng

- Log file chính: `~/.ctxora/logs/ctxora-mcp.log`
- Legacy symlink: `~/.gemini/mcp-harness-v3.log` vẫn được tạo tự động nếu hệ thống cho phép
- Config path `~/.gemini/antigravity/mcp_config.json` phải trỏ đến `server.py` (không phải legacy script)
- Server tự động load model embeddings khi khởi động lần đầu (có thể mất vài giây)
