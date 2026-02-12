/**
 * IO utilities for Blueprint hooks
 * Shared stdin reading logic used across all ESM hooks
 */

/**
 * Read stdin with timeout protection.
 * Used by all Blueprint hooks to parse Claude Code's JSON input.
 * @param {number} timeoutMs - Timeout in milliseconds (default: 4000)
 * @returns {Promise<string>} Raw stdin content
 */
export function readStdin(timeoutMs = 4000) {
  return new Promise((resolve) => {
    const chunks = [];
    let settled = false;
    const timeout = setTimeout(() => {
      if (!settled) {
        settled = true;
        process.stdin.removeAllListeners();
        try { process.stdin.destroy(); } catch { /* ignore */ }
        resolve(Buffer.concat(chunks).toString('utf-8'));
      }
    }, timeoutMs);
    process.stdin.on('data', (chunk) => { chunks.push(chunk); });
    process.stdin.on('end', () => {
      if (!settled) { settled = true; clearTimeout(timeout); resolve(Buffer.concat(chunks).toString('utf-8')); }
    });
    process.stdin.on('error', () => {
      if (!settled) { settled = true; clearTimeout(timeout); resolve(''); }
    });
    if (process.stdin.readableEnded) {
      if (!settled) { settled = true; clearTimeout(timeout); resolve(Buffer.concat(chunks).toString('utf-8')); }
    }
  });
}
