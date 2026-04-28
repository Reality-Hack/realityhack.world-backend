#!/usr/bin/env bash
set -euo pipefail

# Usage examples:
#   ./deploy_scripts/change_logs.sh frontend
#   ./deploy_scripts/change_logs.sh backend branch=dev2
#   ./deploy_scripts/change_logs.sh backend commit=abc1234
#   ./deploy_scripts/change_logs.sh frontend branch=feature/foo commit=4f2c1d9

TARGET="${1:-}"

if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 <frontend|backend> [branch=<name>] [commit=<sha>] [show-files=<true|false>]"
  exit 1
fi

BRANCH_OVERRIDE=""
COMMIT_OVERRIDE=""

# Parse named params after target
for arg in "${@:2}"; do
  case "$arg" in
    branch=*)
      BRANCH_OVERRIDE="${arg#branch=}"
      ;;
    commit=*)
      COMMIT_OVERRIDE="${arg#commit=}"
      ;;
    show-files=*)
      SHOW_FILES="${arg#show-files=}"
      ;;
    *)
      echo "Unknown parameter: $arg"
      echo "Allowed: branch=<name> commit=<sha> show-files=<true|false>"
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_REPO="$(cd "$SCRIPT_DIR/../../realityhack.world-frontend" && pwd)"

case "$TARGET" in
  frontend)
    REPO_PATH="$FRONTEND_REPO"
    DEFAULT_COMPARE_BRANCH="dev2"
    ;;
  backend)
    REPO_PATH="$BACKEND_REPO"
    DEFAULT_COMPARE_BRANCH="dev"
    ;;
  *)
    echo "Invalid target: '$TARGET'. Expected 'frontend' or 'backend'."
    exit 1
    ;;
esac

BASE_BRANCH="main"
COMPARE_BRANCH="${BRANCH_OVERRIDE:-$DEFAULT_COMPARE_BRANCH}"
REMOTE_NAME="upstream"

cd "$REPO_PATH"

if ! git remote get-url "$REMOTE_NAME" >/dev/null 2>&1; then
  echo "Remote '$REMOTE_NAME' not found in $REPO_PATH"
  exit 1
fi

BASE_REF="$REMOTE_NAME/$BASE_BRANCH"
COMPARE_REF="$REMOTE_NAME/$COMPARE_BRANCH"

if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
  echo "Branch '$BASE_REF' not found in $REPO_PATH"
  exit 1
fi

if ! git rev-parse --verify "$COMPARE_REF" >/dev/null 2>&1; then
  echo "Branch '$COMPARE_REF' not found in $REPO_PATH"
  exit 1
fi

if [[ -n "$COMMIT_OVERRIDE" ]]; then
  if ! git rev-parse --verify "${COMMIT_OVERRIDE}^{commit}" >/dev/null 2>&1; then
    echo "Commit '$COMMIT_OVERRIDE' not found in $REPO_PATH"
    exit 1
  fi
fi

echo "========================================"
echo "Repo: $REPO_PATH"
echo "Remote: $REMOTE_NAME"
echo "Diff range: $BASE_REF...$COMPARE_REF"
if [[ -n "$COMMIT_OVERRIDE" ]]; then
  echo "Changelog range: $COMMIT_OVERRIDE..$COMPARE_REF"
else
  echo "Changelog range: $BASE_REF..$COMPARE_REF"
fi
echo "========================================"
echo
SHOW_FILES="${SHOW_FILES:-false}"

if [[ "$SHOW_FILES" == "true" ]]; then
  echo "Changed files:"
  git diff --name-status "$BASE_REF...$COMPARE_REF"
  echo
fi

echo "Changelog (commit messages):"
if [[ -n "$COMMIT_OVERRIDE" ]]; then
  git log --no-merges --pretty=format:"- %s (%h)" "$COMMIT_OVERRIDE..$COMPARE_REF" || true
else
  git log --no-merges --pretty=format:"- %s (%h)" "$BASE_REF..$COMPARE_REF" || true
fi
echo