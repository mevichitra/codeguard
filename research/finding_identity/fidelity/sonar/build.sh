#!/usr/bin/env bash
# Compile SonarQube's issue tracker, unmodified, with SonarTrackerHarness.java.
#
# Fetches the tracker sources at a pinned SonarQube tag and the exact dependency versions
# that tag declares (build.gradle), verifies the jars' SHA-256, and compiles everything
# into fidelity/.build/sonar. Needs git, curl and a JDK (17 or later).
set -euo pipefail

TAG=26.10.0.133078
COMMIT=55989c640a19aac3cb1c190f97464e59773035c5
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$HERE/../.build/sonar
MAVEN=https://repo1.maven.org/maven2

JARS=(
  "com/google/guava/guava/33.7.1-jre/guava-33.7.1-jre.jar 796d8e28ac64e83a47c4c5935a8fecc4682650a04bbdead738ef0f5a3a0e6c46"
  "com/google/guava/failureaccess/1.0.3/failureaccess-1.0.3.jar cbfc3906b19b8f55dd7cfd6dfe0aa4532e834250d7f080bd8d211a3e246b59cb"
  "commons-codec/commons-codec/1.22.1/commons-codec-1.22.1.jar 78a5d732fbd715e2d10bd7150d2f8030bae57267f8aacc5c88f642cb6c2e5d3f"
  "org/apache/commons/commons-lang3/3.20.0/commons-lang3-3.20.0.jar 69e5c9fa35da7a51a5fd2099dfe56a2d8d32cf233e2f6d770e796146440263f4"
  "com/google/code/findbugs/jsr305/3.0.2/jsr305-3.0.2.jar 766ad2a0783f2687962c8ad74ceecc38a28b9f72a2d085ee438b7813e928d0c7"
  "org/sonarsource/api/plugin/sonar-plugin-api/14.1.0.5543/sonar-plugin-api-14.1.0.5543.jar ac70438a14ba2de9459b8c4d8662396c4ff9c5917166dccf5faf30500f322f31"
)

mkdir -p "$OUT/lib" "$OUT/classes"

if [ ! -d "$OUT/sonarqube/.git" ]; then
  git -c advice.detachedHead=false clone --quiet --depth 1 --branch "$TAG" --filter=blob:none --sparse \
    https://github.com/SonarSource/sonarqube "$OUT/sonarqube"
  git -C "$OUT/sonarqube" sparse-checkout set --no-cone \
    'sonar-core/src/main/java/org/sonar/core/issue/tracking/*' \
    'sonar-core/src/main/java/org/sonar/core/hash/*'
fi
test "$(git -C "$OUT/sonarqube" rev-parse HEAD)" = "$COMMIT"

CP=""
for entry in "${JARS[@]}"; do
  path=${entry% *}
  sum=${entry#* }
  jar=$OUT/lib/$(basename "$path")
  [ -f "$jar" ] || curl -sSfL --retry 4 --retry-delay 4 -o "$jar" "$MAVEN/$path"
  echo "$sum  $jar" | sha256sum --check --quiet
  CP=$CP:$jar
done

SRC=$OUT/sonarqube/sonar-core/src/main/java/org/sonar/core
# Trackable.java imports DefaultIssue for a javadoc link only; drop that import so the
# tracker compiles without the rest of sonar-core. No code is changed.
mkdir -p "$OUT/src"
cp "$SRC"/issue/tracking/*.java "$SRC"/hash/SourceLineHashesComputer.java "$OUT/src/"
sed -i '/^import org.sonar.core.issue.DefaultIssue;/d' "$OUT/src/Trackable.java"
rm -f "$OUT/src/AnticipatedTransitionTracker.java" "$OUT/src/package-info.java"

javac -nowarn -d "$OUT/classes" -cp "${CP#:}" "$OUT"/src/*.java "$HERE/SonarTrackerHarness.java"
echo "${CP#:}:$OUT/classes" > "$OUT/classpath"
echo "built $OUT (SonarQube $TAG)"
