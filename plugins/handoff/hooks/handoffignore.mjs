/**
 * Handoff Ignore Module
 *
 * Provides .handoffignore support for excluding specific files/paths
 * from the "Files Modified" section of handoff documents.
 * Uses gitignore-compatible glob matching without external dependencies.
 */

import * as fs from 'fs';
import * as path from 'path';

/**
 * Convert a gitignore-style pattern to a RegExp.
 *
 * Supports:
 * - `*` matches anything except `/`
 * - `**` matches anything including `/`
 * - `?` matches a single character except `/`
 * - Trailing `/` anchors to directories (stripped before matching)
 * - Leading `/` anchors to project root
 *
 * @param {string} pattern - A single gitignore-style pattern
 * @returns {RegExp} Compiled regular expression
 */
function patternToRegExp(pattern) {
  let p = pattern;

  // Trailing slash means directory-only; strip it for matching purposes
  // (callers should normalise directory paths to include trailing /)
  const dirOnly = p.endsWith('/');
  if (dirOnly) {
    p = p.slice(0, -1);
  }

  // Leading slash means root-anchored; otherwise match anywhere
  const rooted = p.startsWith('/');
  if (rooted) {
    p = p.slice(1);
  }

  // Also treat patterns containing a middle `/` as rooted
  const implicitlyRooted = rooted || (p.includes('/') && !p.startsWith('**/'));

  // Escape regex special chars except glob wildcards we handle
  let regex = '';
  let i = 0;
  while (i < p.length) {
    const ch = p[i];

    if (ch === '*') {
      if (p[i + 1] === '*') {
        if (p[i + 2] === '/') {
          // `**/` — matches zero or more directories
          regex += '(?:.+/)?';
          i += 3;
          continue;
        }
        // trailing `**` — matches everything
        regex += '.*';
        i += 2;
        continue;
      }
      // single `*` — matches anything except `/`
      regex += '[^/]*';
      i += 1;
      continue;
    }

    if (ch === '?') {
      regex += '[^/]';
      i += 1;
      continue;
    }

    // Escape regex meta characters
    if ('^$.|+()[]{}\\'.includes(ch)) {
      regex += '\\' + ch;
      i += 1;
      continue;
    }

    regex += ch;
    i += 1;
  }

  // Anchor the pattern
  if (implicitlyRooted) {
    regex = '^' + regex;
  } else {
    // Match at any directory level
    regex = '(?:^|/)' + regex;
  }

  // For directory-only patterns, require a trailing `/` or end-of-string
  if (dirOnly) {
    regex += '(?:/|$)';
  } else {
    // Also match if the pattern matches a prefix directory
    regex += '(?:/.*)?$';
  }

  return new RegExp(regex);
}

/**
 * Parse a .handoffignore file content into structured pattern objects.
 *
 * @param {string} content - Raw file content
 * @returns {Array<{negate: boolean, regex: RegExp}>} Parsed patterns
 */
function parsePatterns(content) {
  const lines = content.split('\n');
  const patterns = [];

  for (const raw of lines) {
    const line = raw.trim();

    // Skip empty lines and comments
    if (!line || line.startsWith('#')) continue;

    // Negation patterns
    const negate = line.startsWith('!');
    const pattern = negate ? line.slice(1) : line;

    if (!pattern) continue;

    patterns.push({
      negate,
      regex: patternToRegExp(pattern),
    });
  }

  return patterns;
}

/**
 * Load ignore patterns from a .handoffignore file in the project root.
 * Returns an empty array if the file does not exist.
 *
 * @param {string} projectRoot - Absolute path to the project root
 * @returns {string[]} Raw pattern lines (comments and blanks excluded)
 */
export function loadIgnorePatterns(projectRoot) {
  const filePath = path.join(projectRoot, '.handoffignore');

  try {
    if (!fs.existsSync(filePath)) {
      return [];
    }
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split('\n');
    const patterns = [];

    for (const raw of lines) {
      const line = raw.trim();
      if (!line || line.startsWith('#')) continue;
      patterns.push(line);
    }

    return patterns;
  } catch {
    // File unreadable — treat as empty
    return [];
  }
}

/**
 * Check whether a file path matches any of the given ignore patterns.
 * Follows gitignore semantics: later negation patterns (`!`) can re-include.
 *
 * @param {string} filePath - Relative file path (forward slashes)
 * @param {string[]} patterns - Pattern strings from loadIgnorePatterns()
 * @returns {boolean} True if the file should be ignored
 */
export function shouldIgnore(filePath, patterns) {
  if (!patterns || patterns.length === 0) return false;

  // Normalise path separators to forward slashes
  const normalised = filePath.replace(/\\/g, '/').replace(/^\//, '');

  const parsed = parsePatterns(patterns.join('\n'));

  let ignored = false;

  for (const { negate, regex } of parsed) {
    if (regex.test(normalised)) {
      ignored = !negate;
    }
  }

  return ignored;
}

/**
 * Filter an array of file paths, removing those matched by .handoffignore.
 *
 * @param {string[]} filePaths - Array of file paths (absolute or relative)
 * @param {string} projectRoot - Absolute path to the project root
 * @returns {string[]} File paths that are NOT ignored
 */
export function filterFiles(filePaths, projectRoot) {
  const patterns = loadIgnorePatterns(projectRoot);
  if (patterns.length === 0) return filePaths;

  const parsed = parsePatterns(patterns.join('\n'));
  const root = projectRoot.replace(/\\/g, '/').replace(/\/$/, '');

  return filePaths.filter((fp) => {
    // Normalise to forward slashes and make relative to project root
    let normalised = fp.replace(/\\/g, '/');
    if (normalised.startsWith(root + '/')) {
      normalised = normalised.slice(root.length + 1);
    }
    normalised = normalised.replace(/^\//, '');

    let ignored = false;
    for (const { negate, regex } of parsed) {
      if (regex.test(normalised)) {
        ignored = !negate;
      }
    }

    return !ignored;
  });
}
