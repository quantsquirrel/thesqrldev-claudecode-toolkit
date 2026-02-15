#!/usr/bin/env node
/**
 * Handoff Recovery Script
 *
 * Checks for interrupted handoff generation and provides recovery information.
 * Looks for draft files and lock files to help resume interrupted work.
 *
 * Usage:
 *   node recover.mjs
 */

import * as fs from 'fs';
import * as path from 'path';
import { homedir } from 'os';
import { checkLock } from './lockfile.mjs';
import { DRAFT_FILE_PREFIX } from './constants.mjs';

/**
 * Find all draft files
 */
export function findDraftFiles() {
  const handoffDir = path.join(process.cwd(), '.claude', 'handoffs');
  const globalHandoffDir = path.join(homedir(), '.claude', 'handoffs');
  const drafts = [];

  for (const dir of [handoffDir, globalHandoffDir]) {
    try {
      if (fs.existsSync(dir)) {
        const files = fs.readdirSync(dir);
        for (const file of files) {
          if (file.startsWith(DRAFT_FILE_PREFIX) && file.endsWith('.json')) {
            const filePath = path.join(dir, file);
            const stat = fs.statSync(filePath);
            const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
            drafts.push({
              path: filePath,
              file,
              data,
              mtime: stat.mtime,
            });
          }
        }
      }
    } catch (e) {
      console.error(`Error reading directory ${dir}:`, e.message);
    }
  }

  return drafts.sort((a, b) => b.mtime - a.mtime); // Most recent first
}

/**
 * Format file size
 */
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Format timestamp
 */
function formatTime(date) {
  return new Date(date).toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Main recovery function
 */
function main() {
  console.log('🔍 Handoff 복구 정보 확인 중...\n');

  // Check lock file
  const lock = checkLock();
  if (lock) {
    console.log('🔒 중단된 생성 작업 발견:');
    console.log(`   세션 ID: ${lock.sessionId}`);
    console.log(`   주제: ${lock.topic}`);
    console.log(`   시작 시간: ${formatTime(lock.startTime)}`);
    console.log('');
  }

  // Check draft files
  const drafts = findDraftFiles();
  if (drafts.length > 0) {
    console.log(`📋 ${drafts.length}개의 초안 발견:\n`);
    drafts.forEach((draft, i) => {
      console.log(`${i + 1}. ${draft.file}`);
      console.log(`   경로: ${draft.path}`);
      console.log(`   생성 시간: ${formatTime(draft.mtime)}`);
      console.log(`   세션 ID: ${draft.data.sessionId || 'N/A'}`);
      console.log(`   추정 토큰: ${draft.data.estimatedTokens?.toLocaleString() || 'N/A'}`);
      console.log(`   작업 디렉토리: ${draft.data.cwd || 'N/A'}`);
      if (draft.data.gitBranch) {
        console.log(`   Git 브랜치: ${draft.data.gitBranch}`);
      }
      console.log('');
    });

    console.log('💡 복구 방법:');
    console.log('   1. 가장 최근 초안 파일 내용 확인');
    console.log('   2. 필요한 정보 복사하여 새 세션에서 계속 진행');
    console.log('   3. 초안 파일은 수동으로 삭제 가능');
  } else if (!lock) {
    console.log('✅ 복구할 항목이 없습니다.');
  }

  console.log('');
}

main();
