#!/usr/bin/env bash
# Produce main-style jar (unbounded list) from current tree by swapping list API sources to febb4d9.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REF="${MAIN_REF:-febb4d9}"
OUT_JAR="$ROOT/target/player-service-java-main-demo.jar"
STASH="$ROOT/.demo-build-main-swap"

restore() {
  if [[ -d "$STASH" ]]; then
    cp -f "$STASH"/PlayerService.java "$ROOT/src/main/java/com/app/playerservicejava/service/"
    cp -f "$STASH"/PlayerController.java "$ROOT/src/main/java/com/app/playerservicejava/controller/"
    cp -f "$STASH"/Players.java "$ROOT/src/main/java/com/app/playerservicejava/model/"
    rm -rf "$STASH"
  fi
}
trap restore EXIT

mkdir -p "$STASH"
cp "$ROOT/src/main/java/com/app/playerservicejava/service/PlayerService.java" "$STASH/"
cp "$ROOT/src/main/java/com/app/playerservicejava/controller/PlayerController.java" "$STASH/"
cp "$ROOT/src/main/java/com/app/playerservicejava/model/Players.java" "$STASH/"

git show "$REF:src/main/java/com/app/playerservicejava/service/PlayerService.java" \
  >"$ROOT/src/main/java/com/app/playerservicejava/service/PlayerService.java"
git show "$REF:src/main/java/com/app/playerservicejava/controller/PlayerController.java" \
  >"$ROOT/src/main/java/com/app/playerservicejava/controller/PlayerController.java"
git show "$REF:src/main/java/com/app/playerservicejava/model/Players.java" \
  >"$ROOT/src/main/java/com/app/playerservicejava/model/Players.java"

(cd "$ROOT" && mvn -q -DskipTests package)
cp "$ROOT/target/player-service-java-0.0.1-SNAPSHOT.jar" "$OUT_JAR"
restore
trap - EXIT
# Refresh branch jar — mvn package during swap overwrites SNAPSHOT.jar with main-list code.
(cd "$ROOT" && mvn -q -DskipTests package)
echo "$OUT_JAR"
