#!/usr/bin/env bash
set -e

# Перевірка, чи передано хеш коміту
if [ -z "$1" ]; then
  echo "Помилка: Вкажіть хеш коміту як аргумент."
  echo "Використання: $0 <COMMIT_HASH>"
  exit 1
fi

COMMIT_HASH="$1"

if [ ! -f "git-filter-repo" ]; then
  wget https://raw.githubusercontent.com/newren/git-filter-repo/main/git-filter-repo
fi

echo "o-murphy <thehelixpg@gmail.com> <noreply@anthropic.com>" > .mailmap_tmp

trap 'rm -f .mailmap_tmp' EXIT

python3 git-filter-repo --mailmap .mailmap_tmp --refs "$COMMIT_HASH..HEAD" --message-callback '
  lines = message.decode("utf-8").splitlines()
  filtered = [
    l for l in lines 
    if not l.startswith("Co-Authored-By: Claude") 
    and not l.startswith("Claude-Session:")
  ]
  return "\n".join(filtered).encode("utf-8")
' --force