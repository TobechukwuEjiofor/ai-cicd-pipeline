#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const LOG_FILE = path.join(__dirname, '..', 'build-history', 'build-log.csv');

function getEnv(name, fallback = '') {
  return process.env[name] || fallback;
}

function main() {
  const result = getEnv('BUILD_RESULT', 'unknown'); // "success" or "failure"
  const durationSeconds = getEnv('BUILD_DURATION_SECONDS', '0');
  const filesChangedRaw = getEnv('FILES_CHANGED', '');
  const linesAdded = getEnv('LINES_ADDED', '0');
  const linesDeleted = getEnv('LINES_DELETED', '0');
  const commitSha = getEnv('COMMIT_SHA', 'unknown');

  const now = new Date();
  const timestamp = now.toISOString();
  const dayOfWeek = now.getUTCDay(); // 0 = Sunday
  const hourUtc = now.getUTCHours();

  const filesChanged = filesChangedRaw
    .split(/\r?\n/)
    .map((f) => f.trim())
    .filter(Boolean);

  // Categorize which parts of the app this build touched -- this becomes
  // a key feature for the failure-prediction model later.
  const modulesTouched = new Set();
  for (const file of filesChanged) {
    if (file.startsWith('src/routes/')) modulesTouched.add('routes');
    else if (file.startsWith('src/middleware/')) modulesTouched.add('middleware');
    else if (file.startsWith('tests/')) modulesTouched.add('tests');
    else if (file.startsWith('src/')) modulesTouched.add('src-core');
    else if (file.startsWith('.github/')) modulesTouched.add('ci-config');
    else modulesTouched.add('other');
  }

  const row = [
    timestamp,
    dayOfWeek,
    hourUtc,
    filesChanged.length,
    linesAdded,
    linesDeleted,
    Array.from(modulesTouched).join('|') || 'none',
    result,
    durationSeconds,
    commitSha,
  ];

  const escapeCsv = (val) => {
    const str = String(val);
    return /[,"\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str;
  };
  const line = row.map(escapeCsv).join(',') + '\n';

  fs.mkdirSync(path.dirname(LOG_FILE), { recursive: true });

  if (!fs.existsSync(LOG_FILE)) {
    const header = [
      'timestamp', 'day_of_week', 'hour_utc', 'files_changed_count',
      'lines_added', 'lines_deleted', 'modules_touched', 'result',
      'duration_seconds', 'commit_sha',
    ].join(',') + '\n';
    fs.writeFileSync(LOG_FILE, header);
  }

  fs.appendFileSync(LOG_FILE, line);
  console.log('Logged build:', line.trim());
}

main();
