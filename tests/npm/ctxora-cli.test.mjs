import assert from "node:assert/strict";
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import test from "node:test";

import { compareVersions, findPython, isSupportedPython, parsePythonVersion, runtimePython } from "../../bin/ctxora.mjs";

const ROOT = new URL("../../", import.meta.url);
const CLI = fileURLToPath(new URL("bin/ctxora.mjs", ROOT));

test("accepts only supported CPython minor versions", () => {
  assert.deepEqual(parsePythonVersion("Python 3.12.4\n"), [3, 12, 4]);
  assert.equal(isSupportedPython([3, 10, 0]), true);
  assert.equal(isSupportedPython([3, 13, 9]), true);
  assert.equal(isSupportedPython([3, 9, 20]), false);
  assert.equal(isSupportedPython([3, 14, 0]), false);
});

test("compares stable release versions deterministically", () => {
  assert.equal(compareVersions("6.4.0", "6.5.1"), -1);
  assert.equal(compareVersions("6.5.1", "6.5.1"), 0);
  assert.equal(compareVersions("7.0.0", "6.5.1"), 1);
  assert.equal(compareVersions("latest", "6.5.1"), null);
});

test("falls back to a supported versioned Python executable", { skip: process.platform === "win32" }, () => {
  const directory = mkdtempSync(join(tmpdir(), "ctxora-python-test-"));
  const legacyPython = join(directory, "python3");
  const supportedPython = join(directory, "python3.12");
  writeFileSync(legacyPython, "#!/bin/sh\nprintf 'Python 3.9.6\\n'\n");
  writeFileSync(supportedPython, "#!/bin/sh\nprintf 'Python 3.12.14\\n'\n");
  chmodSync(legacyPython, 0o755);
  chmodSync(supportedPython, 0o755);

  const originalPath = process.env.PATH;
  process.env.PATH = `${directory}:${originalPath ?? ""}`;
  try {
    assert.deepEqual(findPython(), { command: "python3.12", prefix: [] });
  } finally {
    process.env.PATH = originalPath;
  }
});

test("reports the npm package version without installing Python", () => {
  const result = spawnSync(process.execPath, [CLI, "--version"], {
    encoding: "utf8",
  });
  assert.equal(result.status, 0);
  assert.equal(result.stdout.trim(), "6.5.1");
});

test("runs through an npm-style executable symlink", { skip: process.platform === "win32" }, () => {
  const directory = mkdtempSync(join(tmpdir(), "ctxora-bin-test-"));
  const executable = join(directory, "ctxora");
  symlinkSync(CLI, executable);
  const result = spawnSync(executable, ["--version"], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout.trim(), "6.5.1");
});

test("passes commands to an existing managed runtime with stable MCP launcher settings", { skip: process.platform === "win32" }, () => {
  const home = mkdtempSync(join(tmpdir(), "ctxora-npm-test-"));
  const runtime = join(home, "runtime", "6.5.1");
  const python = runtimePython(runtime);
  const capture = join(home, "capture.json");
  mkdirSync(join(runtime, "venv", "bin"), { recursive: true });
  writeFileSync(join(runtime, "install.json"), '{"packageVersion":"6.5.1"}\n');
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

test("npm package contains canonical artifacts and compatibility projections", () => {
  const result = spawnSync("npm", ["pack", "--dry-run", "--json"], {
    cwd: fileURLToPath(ROOT),
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stderr);
  const files = new Set(JSON.parse(result.stdout)[0].files.map((file) => file.path));
  for (const path of [
    "src/harness_context/artifacts/canonical/agents/ctxora-planner.md",
    "src/harness_context/artifacts/manifests/artifacts.json",
    "agents/ctxora-planner.md",
    "commands/plan.md",
    "skills/ctxora-navigation/SKILL.md",
  ]) {
    assert.equal(files.has(path), true, `${path} must be present in the npm package`);
  }
});
