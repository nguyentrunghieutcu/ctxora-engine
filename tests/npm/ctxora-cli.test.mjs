import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readFileSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import test from "node:test";

import { isSupportedPython, parsePythonVersion, runtimePython } from "../../bin/ctxora.mjs";

const ROOT = new URL("../../", import.meta.url);
const CLI = fileURLToPath(new URL("bin/ctxora.mjs", ROOT));

test("accepts only supported CPython minor versions", () => {
  assert.deepEqual(parsePythonVersion("Python 3.12.4\n"), [3, 12, 4]);
  assert.equal(isSupportedPython([3, 10, 0]), true);
  assert.equal(isSupportedPython([3, 13, 9]), true);
  assert.equal(isSupportedPython([3, 9, 20]), false);
  assert.equal(isSupportedPython([3, 14, 0]), false);
});

test("reports the npm package version without installing Python", () => {
  const result = spawnSync(process.execPath, [CLI, "--version"], {
    encoding: "utf8",
  });
  assert.equal(result.status, 0);
  assert.equal(result.stdout.trim(), "6.2.0");
});

test("runs through an npm-style executable symlink", { skip: process.platform === "win32" }, () => {
  const directory = mkdtempSync(join(tmpdir(), "ctxora-bin-test-"));
  const executable = join(directory, "ctxora");
  symlinkSync(CLI, executable);
  const result = spawnSync(executable, ["--version"], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout.trim(), "6.2.0");
});

test("passes commands to an existing managed runtime with stable MCP launcher settings", { skip: process.platform === "win32" }, () => {
  const home = mkdtempSync(join(tmpdir(), "ctxora-npm-test-"));
  const runtime = join(home, "runtime", "6.2.0");
  const python = runtimePython(runtime);
  const capture = join(home, "capture.json");
  mkdirSync(join(runtime, "venv", "bin"), { recursive: true });
  writeFileSync(join(runtime, "install.json"), '{"packageVersion":"6.2.0"}\n');
  writeFileSync(python, `#!/bin/sh\nprintf '%s' "$CTXORA_MCP_COMMAND|$CTXORA_MCP_ARGS_PREFIX|$*" > "${capture}"\n`);
  spawnSync("chmod", ["+x", python]);

  const result = spawnSync(process.execPath, [CLI, "setup", "--workspace", "."], {
    encoding: "utf8",
    env: { ...process.env, CTXORA_HOME: home },
  });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(
    readFileSync(capture, "utf8"),
    `${python}|["-m","harness_context.cli.app"]|-m harness_context.cli.app setup --workspace .`,
  );
});
