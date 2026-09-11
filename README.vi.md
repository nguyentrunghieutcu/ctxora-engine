<div align="center">

<a href="https://ctxora-landing.vercel.app/">
  <img src="assets/ctxora-app-icon.png" alt="Biểu tượng CTXORA" width="128" height="128">
</a>

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

[Website](https://ctxora-landing.vercel.app/) · [Bắt đầu nhanh](#bắt-đầu-nhanh) · [Cài đặt](#cài-đặt) · [Agent skills](#agent-skills) · [CLI](#tham-chiếu-cli) · [MCP](#mcp-tools) · [Bảo mật](#quyền-riêng-tư-và-bảo-mật)

</div>

> [!IMPORTANT]
> **Nguồn chính thức:** dùng package `ctxora` trên npm hoặc GitHub repository này. Gói `ctxora-engine` không được phát hành trên PyPI. Các package bên thứ ba sử dụng tên CTXORA không được dự án duy trì hoặc kiểm duyệt.

CTXORA Engine xây dựng biểu diễn local có thể tái sử dụng của repository và cung cấp đúng evidence cho Codex, Claude Code, Cursor, GitHub Copilot hoặc bất kỳ agent hỗ trợ MCP nào. Source code, index, embedding, graph, memory và handoff đều nằm trên máy của bạn.

## Bắt đầu nhanh

### Thiết lập project của bạn

Chạy các lệnh sau tại repository mà coding agent cần hiểu:

```bash
npx ctxora setup --workspace .
npx ctxora index --workspace .
npx ctxora install --workspace . --profile claude-code --dry-run
npx ctxora install --workspace . --profile claude-code
npx ctxora explain --workspace . \
  "Authentication được triển khai ở đâu?"
```

Sau đó khởi động lại coding client. Hai lệnh đầu tạo và index workspace local; `install` kết nối MCP server với Claude Code. Dùng `--profile codex`, `--profile cursor` hoặc `--profile generic-mcp` cho client khác. Kết quả là JSON có file, symbol, provenance, coverage diagnostics và test đề xuất khi có.

Nếu chỉ muốn dùng CLI, chạy `npx ctxora query --workspace . "mô tả task"`. Nếu setup lỗi, chạy `npx ctxora doctor --workspace .` trước khi thử lại.

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
- Luồng setup, indexing, retrieval và MCP startup độc lập framework, được kiểm thử với Python, TypeScript, Flutter, Go, Rust, Java, Kotlin, Swift, PHP và Ruby.
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

Từ `6.5.0`, phiên npm launcher chạy tương tác sẽ kiểm tra release stable mới tối đa một lần mỗi 24 giờ và chỉ hiện thông báo. Có thể tắt bằng `CTXORA_NO_UPDATE_CHECK=1`. CTXORA không bao giờ tự apply update ngầm:

```bash
ctxora update check --workspace .
ctxora update plan --workspace .
ctxora update apply <plan-digest> --workspace . --yes
```

Apply chỉ dùng npm version đã xác thực, kiểm tra global installation, cài lại MCP profile thuộc ownership của CTXORA và skill target dùng profile mặc định, đồng thời rollback nếu lỗi. Skill selection đã tùy biến luôn được giữ lại để người dùng review thủ công.

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

Cài pack CTXORA đã được gom sẵn:

```bash
npx skills add https://www.skills.sh/p/2fCkKUwjcYsPi0WX
```

Liệt kê hoặc chỉ cài một skill:

```bash
npx skills add nguyentrunghieutcu/ctxora-engine --list
npx skills add nguyentrunghieutcu/ctxora-engine --skill ctxora-setup
```

Pack ở cấp repository gồm các workflow riêng của CTXORA: setup, navigation, repository context, health, profile và learning. Phiên bản hiện tại của `skills` CLI yêu cầu Node.js 22.20 trở lên.

CTXORA cũng vendor catalog ECC hiện tại: 286 skill được pin tại commit ECC `e04ea0b9cc8248686edf5ac751cadff550e162b8` ngày 8/9/2026. Bắt đầu từ một ECC profile, kiểm tra rồi tùy biến module hoặc từng skill:

```bash
npx ctxora skills profiles --workspace .
npx ctxora skills modules --workspace .
npx ctxora skills preview --workspace . --profile developer
npx ctxora skills preview --workspace . --profile developer \
  --add-module security --remove-skill security-scan
npx ctxora skills install --workspace . --profile developer \
  --add-module security --remove-skill security-scan
ctxora skills install --workspace . --profile developer \
  --target codex --target claude --target cursor --target gemini
```

Mặc định CTXORA dùng catalog dùng chung trong runtime: `--target all` chỉ ghi profile workspace và năm receipt nhẹ, không copy toàn bộ catalog vào từng host. Dùng `route_skills` hoặc `prepare_context` để inject đúng instruction cần thiết. `--delivery materialized` là chế độ tương thích phải bật rõ ràng cho host cần file cục bộ; cần `--prune` để migrate bản cũ và chỉ xóa skill chưa bị sửa do CTXORA sở hữu. Preview không sửa file và skill đã tùy biến không bao giờ bị ghi đè. Xem provenance và license tại `THIRD_PARTY_NOTICES.md`.

### Command và agent role

Hướng dẫn chính nằm trong `skills/`: dùng `ctxora-navigation` để chọn workflow, `ctxora-workflow-profiles` để chọn và tùy biến ECC skill profile, và `ctxora-continuous-learning` để lưu lesson đã kiểm chứng. Tra routing tại `docs/COMMAND-SKILL-MAP.md`. Skill profile độc lập với client install profile như `codex` hoặc `cursor`.

Skill reranking được giới hạn theo project và dựa trên outcome. Task đã route sẽ xuất hiện dưới dạng fingerprint-only pending cho đến khi `skill_feedback` ghi nhận kết quả đã kiểm chứng; CTXORA không tự suy luận success từ thay đổi Git và không lưu raw prompt. Dùng `ctxora skills learning --workspace .` hoặc Console local để xem task hoàn tất, route đang chờ và tín hiệu boost/penalty hiện tại.

CTXORA cũng cung cấp các template workflow chủ động, lấy cảm hứng từ cách ECC dùng command-first:

| Command | Mục đích | Khả năng CTXORA |
|---|---|---|
| `/ctxora:context <task>` | Lấy bằng chứng repository trước khi code | `plan_context`, `retrieve_context`, `prepare_context` |
| `/ctxora:route <task>` | Tự chọn skill trong profile và học sau validation | `route_skills`, `skill_feedback` |
| `/ctxora:plan <task>` | Lập kế hoạch dựa trên context | `plan_context`, `retrieve_context` |
| `/ctxora:review [scope]` | Review thay đổi với context repository | `retrieve_context` |
| `/ctxora:health` | Kiểm tra workspace và index | `doctor`, `context-score`, `inspect` |
| `/ctxora:handoff save\|restore` | Tiếp tục công việc giữa các session | handoff MCP tools |

Template nằm trong npm package ở `commands/`. Khi cài dưới dạng Claude Code plugin, namespace là `/ctxora:<command>`. Nếu copy thủ công, dùng quy ước tên command của client; client không hỗ trợ slash command có thể dùng workflow tương tự như prompt thường. Chỉ cài MCP server không tự đăng ký slash command.

#### Bật slash command trong Claude Code

Cần cài và đăng nhập Claude Code, đồng thời kết nối MCP như phần trên. Plugin được đóng gói từ npm `6.3.0` và cũng có sẵn trong source checkout chứa `.claude-plugin/plugin.json`, `commands/` và `agents/`.

Thay cả hai đường dẫn bên dưới. Mở Claude Code tại **repository ứng dụng của bạn**, không phải repository source CTXORA:

```bash
cd "/duong-dan-tuyet-doi/toi/project-cua-ban"
claude --plugin-dir "/duong-dan-tuyet-doi/toi/ctxora-engine"
```

Các lần mở sau cũng cần truyền `--plugin-dir`. Trong Claude Code, dùng `/help` kiểm tra command và `/mcp` kiểm tra kết nối CTXORA. Đây là hai bước kiểm tra riêng. Sau đó thử:

```text
/ctxora:plan Thêm tính năng reset mật khẩu
/ctxora:context Trace luồng refresh token
/ctxora:review
/ctxora:health
```

Với Codex hoặc Cursor, chạy `npx ctxora install --workspace . --profile codex` hoặc thay `codex` bằng `cursor`. MCP client khác cần cấu hình riêng; chưa có install profile riêng cho Copilot. Cài MCP không tự làm xuất hiện `/ctxora:*`. Sau khi kết nối, thử prompt thường:

```text
Dùng CTXORA retrieve_context cho workspace này để tìm phần authentication
và test liên quan. Chỉ ra các file và đề xuất kế hoạch; chưa chỉnh sửa code.
```

Không thấy command: kiểm tra đường dẫn plugin. Có command nhưng không gọi được tool: kiểm tra kết nối MCP và chạy `npx ctxora doctor --workspace .` tại repo ứng dụng. Context cũ: chạy `npx ctxora index --workspace . --incremental`.

#### Nên dùng agent nào?

Chọn role theo nhu cầu:

| Nhu cầu | Role | Khi dùng |
|---|---|---|
| Lấy context repository | `ctxora-context-engineer` | Task liên quan repository lạ hoặc nhiều file. |
| Lập kế hoạch triển khai | `ctxora-planner` | Cần file, dependency, rủi ro, test và tiêu chí hoàn tất trước khi sửa. |
| Nghiên cứu một câu hỏi | `ctxora-researcher` | Cần bằng chứng trong repo và nguồn sơ cấp được ghi rõ. |
| Review thay đổi | `ctxora-reviewer` | Cần finding, không cần agent tự sửa. |
| Quản trị setup và session | `ctxora-maintainer` | Cần index, chẩn đoán, memory hoặc handoff. |

Đây là role prompt, không phải các LLM riêng. Agent của host vẫn chịu trách nhiệm chỉnh sửa; CTXORA cung cấp context cục bộ, memory và handoff. Template canonical được đóng gói trong `src/harness_context/artifacts/canonical/`; `agents/`, `commands/` và `skills/` là projection tương thích được tạo cho Claude plugin và hệ sinh thái npm.

Nếu host đã nạp các agent, yêu cầu rõ: "Dùng agent ctxora-reviewer review thay đổi chưa commit; chỉ báo finding, không sửa code." Nếu chưa nạp, yêu cầu assistant hiện tại thực hiện vai trò đó; không mặc định có agent riêng được khởi chạy. Với feature: `plan` → triển khai và chạy test của project → `review`. Với bug: tái hiện lỗi trước, lấy context liên quan rồi mới sửa.

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
| `dashboard` | Mở CTXORA Console loopback với view đã redact và action allowlist theo plan/confirm. |
| `update check`, `update plan`, `update apply` | Kiểm tra, preview và xác nhận npm update có verify/rollback. |
| `export` | Export snapshot ra JSON. |
| `profile` | Liệt kê coding-agent profile được hỗ trợ. |
| `install`, `uninstall` | Thêm hoặc gỡ cấu hình MCP client an toàn. |
| `skills profiles`, `skills modules`, `skills list` | Xem catalog ECC skill đã pin. |
| `skills preview`, `skills install` | Bắt đầu từ profile, tùy biến rồi preview hoặc cài các skill đã chọn. |
| `ci` | Refresh file thay đổi giữa hai Git ref. |
| `generate-agents-md` | Sinh repository instructions cho agent. |
| `generate-copilot-instructions` | Sinh GitHub Copilot instructions. |
| `generate-cursor-rules` | Sinh Cursor rules. |
| `pro` | Hiển thị trạng thái waitlist, không cài paid feature. |

Mọi command đều hỗ trợ `--workspace`. Chạy `ctxora <command> --help` để xem option cụ thể.

## MCP tools

CTXORA MCP hiện cung cấp 21 tools.

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

CTXORA có hai tích hợp ECC độc lập:

- Catalog skill được vendor và pin, dùng để copy guidance đã chọn vào project; không chạy script ECC, bật hook hay cài dependency ngoài.
- Adapter read-only tùy chọn cho vault [`ecc.memory.v1`](https://github.com/affaan-m/ECC); không clone, gọi hoặc sửa bản cài ECC bên ngoài.

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
