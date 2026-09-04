<div align="center">

# CTXORA Engine

### Index once. Ground every agent.

**Context engine local-first dành cho coding agent.**

[![CI](https://github.com/nguyentrunghieutcu/ctxora-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/nguyentrunghieutcu/ctxora-engine/actions/workflows/ci.yml)
[![npm](https://img.shields.io/npm/v/ctxora?logo=npm)](https://www.npmjs.com/package/ctxora)
[![skills.sh](https://skills.sh/b/nguyentrunghieutcu/ctxora-engine)](https://skills.sh/nguyentrunghieutcu/ctxora-engine)
[![Python](https://img.shields.io/badge/Python-3.10--3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-22c55e.svg)](LICENSE)
[![Local first](https://img.shields.io/badge/Context-local--first-7c3aed)](#quyền-riêng-tư-và-bảo-mật)
[![Plan](https://img.shields.io/badge/CTXORA_Free-không_giới_hạn-0ea5e9)](docs/PRICING.md)

[English](README.md) · **Tiếng Việt**

[Bắt đầu nhanh](#bắt-đầu-nhanh) · [Cài đặt](#cài-đặt) · [Agent skills](#agent-skills) · [CLI](#tham-chiếu-cli) · [MCP](#mcp-tools) · [Bảo mật](#quyền-riêng-tư-và-bảo-mật)

</div>

> [!IMPORTANT]
> **Nguồn chính thức:** dùng package `ctxora` trên npm hoặc GitHub repository này. Gói `ctxora-engine` không được phát hành trên PyPI. Các package bên thứ ba sử dụng tên CTXORA không được dự án duy trì hoặc kiểm duyệt.

CTXORA Engine xây dựng biểu diễn local có thể tái sử dụng của repository và cung cấp đúng evidence cho Codex, Claude Code, Cursor, GitHub Copilot hoặc bất kỳ agent hỗ trợ MCP nào. Source code, index, embedding, graph, memory và handoff đều nằm trên máy của bạn.

## Bắt đầu nhanh

```bash
npx ctxora setup --workspace /duong-dan/toi/project
npx ctxora index --workspace /duong-dan/toi/project
npx ctxora explain --workspace /duong-dan/toi/project \
  "Authentication được triển khai ở đâu?"
```

Kết quả là JSON có cấu trúc, gồm file liên quan, symbol, tín hiệu dependency, provenance, coverage diagnostics và test hoặc convention được đề xuất khi có thể xác định.

## Vì sao cần CTXORA?

Coding agent thường tốn token để khám phá lại repository, chọn sai layer, bỏ sót convention hoặc mất context giữa các phiên. Instruction file tĩnh giúp định hướng, nhưng không tự chọn evidence phù hợp với từng task.

CTXORA bổ sung một lớp context local:

```text
Repository
   ↓ scan, parse, chunk
Immutable local snapshot
   ↓ lexical + semantic + symbol + path + graph indexes
Context planner
   ↓ CAG / RAG / long context / graph-augmented retrieval
Codex · Claude Code · Cursor · Copilot · MCP clients
```

- **Giảm sửa sai file** — tìm module, dependency path và test liên quan.
- **Giảm prompt lặp lại** — tái sử dụng kiến thức repository giữa nhiều phiên agent.
- **Không khóa vào một agent** — một engine phục vụ nhiều coding tool.
- **Riêng tư mặc định** — không hosted index, remote telemetry hoặc cloud account bắt buộc.
- **Evidence có thể kiểm tra** — mỗi kết quả đều có source path và provenance.

## Bạn nhận được gì

### Local context engine

- AST-aware chunking cho Python, JavaScript và TypeScript; fallback chunking có giới hạn cho định dạng text khác.
- Hybrid lexical và local semantic retrieval bằng BM25, TF-IDF/LSA, keyword overlap, symbol và path.
- Code dependency graph và graph-augmented context selection.
- Các strategy CAG, RAG, hybrid CAG/RAG, long context và graph augmented.
- Immutable snapshot với candidate validation, atomic promotion, recovery và incremental refresh.
- SQLite memory và raw conversation handoff theo workspace.
- Token budgeting cho context window của OpenAI, Anthropic và Gemini.

### Onboarding coding agent

```bash
ctxora repo-map --workspace .
ctxora context-score --workspace .
ctxora generate-agents-md --workspace .
ctxora generate-copilot-instructions --workspace .
ctxora generate-cursor-rules --workspace .
```

Các instruction file được sinh theo cách deterministic và không ghi đè file hiện có nếu thiếu `--force`.

### An toàn và vận hành

- Authorization theo canonical workspace root và chặn symlink thoát khỏi root.
- Loại secret-like file, binary, dependency, VCS, generated state và file quá lớn.
- Nội dung repository được retrieve luôn là untrusted evidence, không phải agent instruction.
- Machine-readable diagnostics, context health report, evaluation gate và CLI exit code ổn định.
- `ctxora ci` local để index file thay đổi giữa hai Git ref.

## Cài đặt

### npm / npx — khuyến nghị

```bash
npx ctxora setup --workspace /duong-dan/toi/project
npx ctxora doctor --workspace /duong-dan/toi/project
```

Npm launcher không có dependency ngoài, đóng gói source Python MIT và cài CTXORA Engine vào environment local theo version. Không cần cài Python package global hoặc tạo cloud account. Máy cần có sẵn Python 3.10–3.13.

Nếu muốn có shell command lâu dài:

```bash
npm install --global ctxora
ctxora setup --workspace /duong-dan/toi/project
```

### Cài trực tiếp từ GitHub

```bash
python3 -m pip install \
  "git+https://github.com/nguyentrunghieutcu/ctxora-engine.git"
```

### Cài từ source clone

```bash
git clone https://github.com/nguyentrunghieutcu/ctxora-engine.git
cd ctxora-engine
python3 -m pip install .
ctxora doctor --workspace .
```

### Môi trường phát triển

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Yêu cầu: Python 3.10–3.13 và Git. Runtime state nằm trong `.ctxora/`; state `.harness/` cũ vẫn đọc được trong giai đoạn migration.

## Agent skills

Cài toàn bộ CTXORA skills từ repository này:

```bash
npx skills add nguyentrunghieutcu/ctxora-engine
```

Liệt kê hoặc chỉ cài một skill:

```bash
npx skills add nguyentrunghieutcu/ctxora-engine --list
npx skills add nguyentrunghieutcu/ctxora-engine --skill ctxora-setup
```

Pack gồm các workflow setup, grounded repository context và context health. Phiên bản hiện tại của `skills` CLI yêu cầu Node.js 22.20 trở lên.

## Kết nối coding agent

CTXORA có thể cập nhật an toàn cấu hình client được hỗ trợ và giữ nguyên các entry không liên quan:

```bash
ctxora profile --workspace .
ctxora install --workspace . --profile codex
ctxora install --workspace . --profile claude-code
ctxora install --workspace . --profile cursor
ctxora install --workspace . --profile generic-mcp
```

Dùng `--dry-run` để xem trước và `--client-config` để chọn file cấu hình khác mặc định.

| Profile | Cấu hình mặc định |
|---|---|
| Codex | `~/.codex/config.toml` |
| Claude Code | `~/.claude.json` |
| Cursor | `~/.cursor/mcp.json` |
| Generic MCP | `~/.config/mcp/servers.json` |

Cấu hình MCP thủ công:

```json
{
  "mcpServers": {
    "ctxora": {
      "command": "ctxora",
      "args": ["run", "--workspace", "/absolute/path/to/project", "--transport", "stdio"],
      "env": {
        "CTXORA_ALLOWED_ROOTS": "/absolute/path/to/project",
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

Không commit cấu hình client chứa đường dẫn cá nhân.

## Workflow chính

### Tìm hiểu repository

```bash
ctxora setup --workspace .
ctxora index --workspace .
ctxora query --workspace . "Luồng xác thực request hoạt động thế nào?"
ctxora explain --workspace . "Nên sửa token rotation ở đâu?"
ctxora inspect --workspace . snapshot
```

### Refresh file thay đổi

```bash
ctxora index --workspace . --incremental
ctxora ci --workspace . --base origin/main --head HEAD
```

### Chạy MCP server

```bash
# Transport local được khuyến nghị
ctxora run --workspace . --transport stdio

# HTTP local
ctxora run --workspace . --transport streamable-http \
  --host 127.0.0.1 --port 8765
```

Bind HTTP ra ngoài loopback cần `--allow-external` và phải được bảo vệ bằng authorization layer trước khi dùng production.

### Export và sửa local state

```bash
ctxora export --workspace . --output ./ctxora-snapshot.json
ctxora doctor --workspace .
ctxora repair --workspace .
```

## Tham chiếu CLI

| Command | Mục đích |
|---|---|
| `setup` | Tạo cấu hình local cho workspace. |
| `register` | Đăng ký và authorize workspace. |
| `run` | Chạy CTXORA MCP foreground. |
| `start`, `status`, `stop` | Quản lý background process local. |
| `index` | Build hoặc refresh local snapshot. |
| `query` | Trả về context package có cấu trúc. |
| `explain` | Giải thích vị trí và cách thực hiện thay đổi. |
| `context-score` | Chấm điểm độ sẵn sàng của repository context. |
| `repo-map` | Tạo repository map cô đọng. |
| `inspect` | Xem workspace, snapshot, bundle hoặc ECC state. |
| `doctor`, `repair` | Chẩn đoán hoặc build lại local state. |
| `export` | Export snapshot ra JSON. |
| `profile` | Liệt kê coding-agent profile được hỗ trợ. |
| `install`, `uninstall` | Thêm hoặc gỡ cấu hình MCP client an toàn. |
| `ci` | Refresh file thay đổi giữa hai Git ref. |
| `generate-agents-md` | Sinh repository instructions cho agent. |
| `generate-copilot-instructions` | Sinh GitHub Copilot instructions. |
| `generate-cursor-rules` | Sinh Cursor rules. |
| `pro` | Hiển thị trạng thái waitlist, không cài paid feature. |

Mọi command đều hỗ trợ `--workspace`. Chạy `ctxora <command> --help` để xem option cụ thể.

## MCP tools

CTXORA MCP hiện cung cấp 24 tools.

### Context và workspace

| Tool | Mục đích |
|---|---|
| `register_workspace` | Đăng ký repository root được phép. |
| `refresh_workspace` | Build hoặc incremental refresh snapshot. |
| `plan_context` | Chọn retrieval strategy cho task. |
| `retrieve_context` | Trả ranked evidence và coverage diagnostics. |
| `prepare_context` | Tạo context package theo token budget. |
| `context_stats` | Xem thống kê index và snapshot. |
| `invalidate_context` | Invalidate index hoặc cached state. |
| `retrieve_context_legacy` | Compatibility entry point cho client cũ. |

### Memory và handoff

| Tool | Mục đích |
|---|---|
| `memory_save`, `memory_search`, `memory_inject` | Lưu, tìm và inject knowledge theo scope. |
| `memory_list`, `memory_delete`, `memory_evict`, `memory_stats` | Quản lý vòng đời local memory. |
| `handoff_conversation` | Lưu raw provider-format conversation handoff. |
| `restore_conversation_handoff` | Khôi phục handoff được chọn rõ ràng. |
| `list_conversation_handoffs` | Liệt kê handoff còn lưu. |
| `delete_conversation_handoff`, `purge_expired_handoffs` | Xóa handoff được chọn hoặc đã hết hạn. |

### Tiện ích

| Tool | Mục đích |
|---|---|
| `estimate_tokens` | Ước tính token cho text. |
| `get_token_budget` | Trả context budget và reserved headroom của model. |
| `invalidate_cache` | Xóa retrieval cache. |
| `reindex_paths` | Force reindex các path được chọn. |

JSON Schema API v2 nằm tại [`schemas/mcp-v2/`](schemas/mcp-v2/).

## Retrieval strategies

| Strategy | Phù hợp với |
|---|---|
| `cag` | Instruction ổn định và repository knowledge cô đọng. |
| `hybrid_rag` | Câu hỏi code cần ranked evidence tập trung. |
| `long_context` | Repository nhỏ nằm trong token budget. |
| `hybrid_cag_rag` | Guidance ổn định kết hợp evidence theo task. |
| `graph_augmented` | Kiến trúc, call path, dependency và impact analysis. |

Planner deterministic và có thể override khi caller cần strategy cụ thể.

## Tích hợp ECC

CTXORA có thể đọc vault format [`ecc.memory.v1`](https://github.com/affaan-m/ECC) như external context tùy chọn. CTXORA không cài, clone, gọi hoặc sửa ECC.

```bash
ctxora run --workspace . --transport stdio --ecc
ctxora inspect --workspace . --ecc ecc
```

Project memory tại `.ecc/memory` chỉ được đọc. User memory tại `~/.ecc/memory` bị tắt trừ khi bật `--ecc-user-scope` hoặc `ecc_allow_user_scope = true`. Memory import có external provenance và trạng thái unreviewed trust.

## Kiến trúc

```text
CLI / MCP / CI transports
          ↓
Application services
          ↓
Domain contracts and planning
          ↓
Local scanners · parsers · indexes · graph · snapshots · SQLite
```

Production package dùng `src/` layout. `harness_context` vẫn là internal Python namespace để tương thích; branding và command public dùng CTXORA. Xem [Architecture](docs/ARCHITECTURE.md) và [OSS release scope](docs/OSS-IMPLEMENTATION-PLAN.md).

## Quyền riêng tư và bảo mật

- Không remote telemetry mặc định.
- Không yêu cầu cloud account hoặc hosted index.
- Workspace root được authorize và canonicalize rõ ràng.
- Symlink không thể thoát khỏi root được phép.
- Secret-like và binary file bị loại trước indexing.
- Retrieved source là untrusted evidence và không thể ghi đè agent instruction.
- External HTTP là opt-in và cần authorization layer do bạn quản lý.

Báo cáo lỗ hổng qua [GitHub Private Vulnerability Reporting](https://github.com/nguyentrunghieutcu/ctxora-engine/security/advisories/new). Nếu kênh đó không dùng được, gửi email tới `nguyentrunghieutcu@gmail.com`. Xem [SECURITY.md](SECURITY.md).

## Free và Pro

### CTXORA Free — đã có

Toàn bộ local engine trong repository MIT này miễn phí và không giới hạn: manual indexing, CAG/RAG/graph retrieval, MCP, local memory, handoff, health tools, repository map và instruction generation.

### CTXORA Pro — waitlist

Phạm vi trả phí dự kiến chỉ gồm managed repository automation, private workflow operations và shared team context. Billing, entitlement, hosted automation và team service chưa được triển khai trong repository này. `ctxora pro` chỉ trả thông tin waitlist.

Xem [product boundary](docs/PRICING.md).

## Cấu trúc project

```text
src/harness_context/   Runtime, domain, application, MCP, CLI, storage
src/chunking/          AST-aware và fallback chunking
src/context/           Assembly, sanitization, token budgeting
src/retrieval/         BM25, local embeddings, graph, reranking, cache
src/memory/            Local episodic và vector memory
src/compact/           Provider handoff và compaction helpers
src/evaluation/        Quality metrics và release gates
bin/                   npm/npx launcher không có dependency ngoài
skills/                Coding-agent skills có thể cài đặt
schemas/mcp-v2/        API v2 JSON Schemas công khai
tests/                 Unit, security, evaluation, E2E, packaging tests
scripts/               Install, uninstall, migration, topology audit
```

## Phát triển và kiểm tra

```bash
npm test
npm pack --dry-run
ruff check .
python scripts/audit_topology.py
python -m unittest discover -s tests -t . -v
python -m evaluation.gates
python -m compileall -q src tests scripts
git diff --check
```

CI matrix chạy Python 3.10, 3.11, 3.12 và 3.13. Evaluation fixture bao gồm Python, TypeScript, Flutter, monorepo, tiếng Việt, malicious prompt-like file, long document và duplicate symbol.

## Xử lý sự cố

### Không tìm thấy `ctxora`

Dùng npm launcher mà không cần cài global command:

```bash
npx ctxora --version
npx ctxora doctor --workspace .
```

### Workspace bị từ chối

Dùng đường dẫn tuyệt đối đang tồn tại và bảo đảm nó nằm trong `CTXORA_ALLOWED_ROOTS` nếu MCP client thiết lập allowlist.

### Instruction file hiện có không được thay thế

Đây là hành vi chủ động để bảo vệ dữ liệu. Kiểm tra output hoặc chỉ chạy lại với `--force` khi thật sự muốn ghi đè.

### HTTP binding bị từ chối

Loopback là security boundary mặc định. Chỉ dùng `--allow-external` phía sau authentication và network-access layer do bạn kiểm soát.

### Cần build lại local state

```bash
ctxora doctor --workspace .
ctxora repair --workspace .
```

## Tài liệu

- [OSS release scope](docs/OSS-IMPLEMENTATION-PLAN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Operations](docs/OPERATIONS.md)
- [Free và Pro boundary](docs/PRICING.md)
- [Security policy](SECURITY.md)
- [Support policy](SUPPORT.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## Cộng đồng

- Mở [GitHub issue](https://github.com/nguyentrunghieutcu/ctxora-engine/issues) cho bug tái hiện được và feature request.
- Dùng private vulnerability reporting cho vấn đề bảo mật.
- Chào đón contribution giữ nguyên local-first và paid-control-plane independence boundary.

## License

CTXORA Engine được phát hành theo [MIT License](LICENSE).
