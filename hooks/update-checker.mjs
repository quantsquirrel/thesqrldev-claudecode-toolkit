#!/usr/bin/env node

// Checks for toolkit updates on session start (24h TTL cache)

import { execSync } from "node:child_process";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PLUGIN_ROOT = join(__dirname, "..");
const CACHE_DIR = join(PLUGIN_ROOT, ".cache");
const CACHE_FILE = join(CACHE_DIR, "update-check.json");
const TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
const REPO = "quantsquirrel/thesqrldev-claudecode-toolkit";

function readCache() {
  try {
    return JSON.parse(readFileSync(CACHE_FILE, "utf-8"));
  } catch {
    return null;
  }
}

function writeCache(data) {
  try {
    mkdirSync(CACHE_DIR, { recursive: true });
    writeFileSync(CACHE_FILE, JSON.stringify(data, null, 2));
  } catch {
    // Ignore cache write failures
  }
}

function getLocalSha() {
  try {
    return execSync("git rev-parse HEAD", {
      cwd: PLUGIN_ROOT,
      encoding: "utf-8",
      timeout: 3000,
    }).trim();
  } catch {
    return null;
  }
}

function getRemoteSha() {
  try {
    const result = execSync(
      `gh api repos/${REPO}/commits/main --jq '.sha'`,
      { encoding: "utf-8", timeout: 5000 }
    ).trim();
    return result || null;
  } catch {
    return null;
  }
}

function main() {
  const cache = readCache();
  const now = Date.now();

  // Skip if checked within TTL
  if (cache && now - cache.checkedAt < TTL_MS) {
    if (cache.updateAvailable) {
      console.log(
        `[toolkit] Update available. Run /toolkit:update or: cd ${PLUGIN_ROOT} && git pull`
      );
    }
    return;
  }

  const localSha = getLocalSha();
  const remoteSha = getRemoteSha();

  if (!localSha || !remoteSha) {
    writeCache({ checkedAt: now, updateAvailable: false });
    return;
  }

  const updateAvailable = localSha !== remoteSha;
  writeCache({ checkedAt: now, localSha, remoteSha, updateAvailable });

  if (updateAvailable) {
    console.log(
      `[toolkit] Update available (${localSha.slice(0, 7)} -> ${remoteSha.slice(0, 7)}). Run /toolkit:update or: cd ${PLUGIN_ROOT} && git pull`
    );
  }
}

main();
