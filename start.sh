#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"

if command -v python3 >/dev/null 2>&1; then
  python_cmd=python3
elif command -v python >/dev/null 2>&1; then
  python_cmd=python
else
  printf '%s\n' 'Python 3.10 이상이 필요합니다. https://www.python.org/downloads/ 에서 설치하세요.' >&2
  exit 1
fi

if ! "$python_cmd" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  printf '%s\n' 'Python 3.10 이상으로 실행하세요.' >&2
  exit 1
fi

printf '%s\n' '영업관리 시스템을 시작합니다.' '브라우저 주소창에 http://localhost:3000 을 입력하세요.' '종료하려면 Ctrl+C를 누르세요.'
exec "$python_cmd" server.py "$@"
