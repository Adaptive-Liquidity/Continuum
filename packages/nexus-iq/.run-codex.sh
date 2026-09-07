#!/usr/bin/env bash
# Generic detached Codex launcher.
# Usage: setsid bash .run-codex.sh <repo_dir> <task_file> <log_file>
cd "$1" || exit 1
exec codex exec \
  -C "$1" \
  --skip-git-repo-check \
  -s danger-full-access \
  -c approval_policy=never \
  - < "$2" \
  > "$3" 2>&1
