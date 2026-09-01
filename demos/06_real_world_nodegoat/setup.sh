#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="${DIR}/.workspace"
REPOSITORY="${WORKSPACE}/NodeGoat"
REPO_URL="https://github.com/OWASP/NodeGoat.git"
REPO_COMMIT="c5cb68a7084e4ae7dcc60e6a98768720a81841e8"

mkdir -p "$WORKSPACE"

if [ ! -d "${REPOSITORY}/.git" ]; then
  echo "Cloning OWASP NodeGoat..."
  git init -q "$REPOSITORY"
  git -C "$REPOSITORY" remote add origin "$REPO_URL"
fi

echo "Fetching pinned revision ${REPO_COMMIT:0:12}..."
git -C "$REPOSITORY" fetch --quiet --depth 1 origin "$REPO_COMMIT"
git -C "$REPOSITORY" checkout --quiet --detach FETCH_HEAD

echo "NodeGoat is ready at: $REPOSITORY"
echo "Revision: $(git -C "$REPOSITORY" rev-parse HEAD)"

