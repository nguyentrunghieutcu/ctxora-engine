---
description: Diagnose CTXORA workspace, index, and context readiness.
argument-hint: [workspace]
---

Run the equivalent CTXORA CLI checks for the current workspace:

```bash
npx ctxora doctor --workspace .
npx ctxora context-score --workspace .
npx ctxora inspect --workspace . snapshot
```

If a workspace argument is provided, replace `.` with it. Explain each failure and propose the smallest repair. Do not delete local state without confirmation.
