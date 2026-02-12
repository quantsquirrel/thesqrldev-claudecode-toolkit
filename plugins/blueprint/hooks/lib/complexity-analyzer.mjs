import { execSync } from 'child_process';
import { resolve } from 'path';

/**
 * Analyze workspace complexity using 3-axis heuristic
 * @param {string} cwd - Working directory
 * @returns {{fileCount: number, locDelta: number, moduleCount: number, preset: string, confidence: number, reasoning: string}}
 */
export function analyzeComplexity(cwd) {
  try {
    // Try git commands in order: staged -> unstaged -> HEAD
    let numstatOutput = '';
    const commands = [
      'git diff --cached --numstat',
      'git diff --numstat',
      'git diff HEAD --numstat'
    ];

    for (const cmd of commands) {
      try {
        numstatOutput = execSync(cmd, { cwd, encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore'] });
        if (numstatOutput.trim()) break;
      } catch (err) {
        continue;
      }
    }

    // No changes found
    if (!numstatOutput.trim()) {
      return {
        fileCount: 0,
        locDelta: 0,
        moduleCount: 0,
        preset: 'standard',
        confidence: 50,
        reasoning: 'Auto-preset: standard (no git changes detected, using default)'
      };
    }

    // Parse numstat: each line is "added\tremoved\tfilepath"
    const lines = numstatOutput.trim().split('\n');
    const files = [];
    let totalAdded = 0;
    let totalRemoved = 0;

    for (const line of lines) {
      const parts = line.split('\t');
      if (parts.length < 3) continue;

      const added = parts[0] === '-' ? 0 : parseInt(parts[0], 10);
      const removed = parts[1] === '-' ? 0 : parseInt(parts[1], 10);
      const filepath = parts[2];

      if (!isNaN(added)) totalAdded += added;
      if (!isNaN(removed)) totalRemoved += removed;
      files.push(filepath);
    }

    // Calculate metrics
    const fileCount = files.length;
    const locDelta = totalAdded + totalRemoved;

    // Calculate moduleCount: unique top-level directories
    const modules = new Set();
    for (const filepath of files) {
      const normalized = filepath.replace(/^\/+/, '');
      const parts = normalized.split('/');
      if (parts.length > 0 && parts[0]) {
        modules.add(parts[0]);
      }
    }
    const moduleCount = modules.size;

    // Apply thresholds
    let preset = 'standard';
    let confidence = 80;

    if (fileCount < 3 && locDelta < 100 && moduleCount <= 1) {
      preset = 'minimal';
      confidence = 90;
    } else if (fileCount > 10 || locDelta > 500 || moduleCount > 3) {
      preset = 'full';
      confidence = 90;
    } else {
      // Standard preset
      confidence = 85;
    }

    const reasoning = `Auto-preset: ${preset} (${fileCount} files, ${locDelta} LOC, ${moduleCount} modules)`;

    return {
      fileCount,
      locDelta,
      moduleCount,
      preset,
      confidence,
      reasoning
    };

  } catch (err) {
    // Fallback to standard if git is not available or errors occur
    return {
      fileCount: 0,
      locDelta: 0,
      moduleCount: 0,
      preset: 'standard',
      confidence: 50,
      reasoning: 'Auto-preset: standard (git unavailable or error, using default)'
    };
  }
}
