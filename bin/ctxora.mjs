#!/usr/bin/env node

import { existsSync, mkdirSync, readFileSync, realpathSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const PACKAGE_VERSION = "6.2.2";
const PYTHON_RANGE = "3.10-3.13";
const PACKAGE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function fail(message) {
  console.error(`ctxora: ${message}`);
  process.exitCode = 1;
}

function run(command, args, options = {}) {
  return spawnSync(command, args, {
    encoding: "utf8",
    stdio: options.capture ? "pipe" : "inherit",
    env: options.env ?? process.env,
  });
}

export function parsePythonVersion(output) {
  const match = output.match(/Python\s+(\d+)\.(\d+)\.(\d+)/);
  return match ? match.slice(1).map(Number) : null;
}

export function isSupportedPython(version) {
  return Boolean(version && version[0] === 3 && version[1] >= 10 && version[1] <= 13);
}

function pythonCandidates() {
  if (process.env.CTXORA_PYTHON) {
    return [{ command: process.env.CTXORA_PYTHON, prefix: [] }];
  }
  const supportedMinors = ["13", "12", "11", "10"];
  return process.platform === "win32"
    ? [
        ...supportedMinors.map((minor) => ({ command: "py", prefix: [`-3.${minor}`] })),
        { command: "python", prefix: [] },
        { command: "python3", prefix: [] },
      ]
    : [
        ...supportedMinors.map((minor) => ({ command: `python3.${minor}`, prefix: [] })),
        { command: "python3", prefix: [] },
        { command: "python", prefix: [] },
      ];
}

export function findPython() {
  for (const candidate of pythonCandidates()) {
    const result = run(candidate.command, [...candidate.prefix, "--version"], { capture: true });
    const version = parsePythonVersion(`${result.stdout ?? ""}${result.stderr ?? ""}`);
    if (!result.error && result.status === 0 && isSupportedPython(version)) {
      return candidate;
    }
  }
  return null;
}

export function runtimeRoot(environment = process.env) {
  if (environment.CTXORA_HOME) return resolve(environment.CTXORA_HOME);
  if (process.platform === "win32") {
    return join(environment.LOCALAPPDATA || join(homedir(), "AppData", "Local"), "CTXORA");
  }
  return join(environment.XDG_DATA_HOME || join(homedir(), ".local", "share"), "ctxora");
}

export function runtimePython(runtimeDirectory) {
  return process.platform === "win32"
    ? join(runtimeDirectory, "venv", "Scripts", "python.exe")
    : join(runtimeDirectory, "venv", "bin", "python");
}

function markerMatches(markerPath) {
  try {
    const marker = JSON.parse(readFileSync(markerPath, "utf8"));
    return marker.packageVersion === PACKAGE_VERSION;
  } catch {
    return false;
  }
}

function installRuntime(systemPython, runtimeDirectory) {
  const parent = dirname(runtimeDirectory);
  mkdirSync(parent, { recursive: true });
  const staging = join(parent, `.install-${process.pid}-${Date.now()}`);
  rmSync(staging, { recursive: true, force: true });

  const create = run(systemPython.command, [...systemPython.prefix, "-m", "venv", join(staging, "venv")]);
  if (create.error || create.status !== 0) {
    rmSync(staging, { recursive: true, force: true });
    throw new Error("could not create the managed Python environment");
  }

  const python = runtimePython(staging);
  const install = run(python, [
    "-m", "pip", "install", "--disable-pip-version-check", "--upgrade", PACKAGE_ROOT,
  ]);
  if (install.error || install.status !== 0) {
    rmSync(staging, { recursive: true, force: true });
    throw new Error("could not install CTXORA Engine into the managed environment");
  }

  writeFileSync(join(staging, "install.json"), `${JSON.stringify({ packageVersion: PACKAGE_VERSION }, null, 2)}\n`);
  rmSync(runtimeDirectory, { recursive: true, force: true });
  renameSync(staging, runtimeDirectory);
}

export function ensureRuntime() {
  const runtimeDirectory = join(runtimeRoot(), "runtime", PACKAGE_VERSION);
  const python = runtimePython(runtimeDirectory);
  if (existsSync(python) && markerMatches(join(runtimeDirectory, "install.json"))) return python;

  const systemPython = findPython();
  if (!systemPython) throw new Error(`Python ${PYTHON_RANGE} is required`);
  installRuntime(systemPython, runtimeDirectory);
  return runtimePython(runtimeDirectory);
}

function printHelp() {
  console.log(`CTXORA Engine ${PACKAGE_VERSION}\n\nUsage:\n  npx ctxora setup --workspace <path>\n  npx ctxora <command> [options]\n\nThe npm launcher installs CTXORA Engine into a versioned local Python environment.\nRun \"npx ctxora setup --help\" for engine command help.`);
}

export function main(args = process.argv.slice(2)) {
  if (args.length === 0 || args[0] === "--help" || args[0] === "-h") {
    printHelp();
    return 0;
  }
  if (args[0] === "--version" || args[0] === "-V") {
    console.log(PACKAGE_VERSION);
    return 0;
  }

  try {
    const python = ensureRuntime();
    const environment = {
      ...process.env,
      CTXORA_MCP_COMMAND: python,
      CTXORA_MCP_ARGS_PREFIX: JSON.stringify(["-m", "harness_context.cli.app"]),
    };
    const result = run(python, ["-m", "harness_context.cli.app", ...args], { env: environment });
    if (result.error) throw result.error;
    return result.status ?? 1;
  } catch (error) {
    fail(error instanceof Error ? error.message : String(error));
    return 1;
  }
}

if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = main();
}
