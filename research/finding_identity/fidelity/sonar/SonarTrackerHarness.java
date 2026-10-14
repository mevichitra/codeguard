// Runs SonarQube's own issue tracker (org.sonar.core.issue.tracking.Tracker) on test cases
// read from stdin, so research/finding_identity/trackers.py can be checked against it.
// build.sh compiles it together with the original tracker sources; see ../README.md.
//
// Input, one token per line, every string base64-encoded UTF-8:
//   CASE
//   OLD <n>   then n lines            the previous version of the file (base)
//   NEW <n>   then n lines            the current version (raw)
//   BASE <k>  then k "<rule> <line> <message>"
//   RAW <k>   then k "<rule> <line> <message>"
//   END
// Output: one line per case, the base index matched to each raw issue (-1 for none).
//
// A line "ORDER k1 k2 ... [| r1 r2 ...]" instead puts the integer keys k, in order, into a
// Guava ArrayListMultimap (the type BlockRecognizer groups lines with), then calls
// removeAll on each r, and prints the multimap's key order.

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collection;
import java.util.Date;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.StringJoiner;
import com.google.common.collect.ArrayListMultimap;
import com.google.common.collect.Multimap;
import org.apache.commons.lang3.StringUtils;
import org.sonar.api.rule.RuleKey;
import org.sonar.core.issue.tracking.BlockHashSequence;
import org.sonar.core.issue.tracking.Input;
import org.sonar.core.issue.tracking.LineHashSequence;
import org.sonar.core.issue.tracking.NonClosedTracking;
import org.sonar.core.issue.tracking.Trackable;
import org.sonar.core.issue.tracking.Tracker;

public class SonarTrackerHarness {
  // Every base issue has the same update date: the port assumes no date ordering.
  private static final Date UPDATED = new Date(0L);

  static final class Issue implements Trackable {
    final RuleKey rule;
    final Integer line;
    final String message;
    final String lineHash;

    Issue(String rule, int line, String message, LineHashSequence hashes) {
      this.rule = RuleKey.of("external_harness", rule);
      this.line = line;
      // TrackerRawInputFactory.toExternalIssue: setMessage only when not empty;
      // DefaultIssue.setMessage abbreviates to MESSAGE_MAX_SIZE.
      this.message = message.isEmpty() ? null : StringUtils.abbreviate(message, 4000);
      // TrackerRawInputFactory.toExternalIssue: the checksum is the start line's hash.
      this.lineHash = hashes.getHashForLine(line);
    }

    @Override public Integer getLine() { return line; }
    @Override public String getMessage() { return message; }
    @Override public String getLineHash() { return lineHash; }
    @Override public RuleKey getRuleKey() { return rule; }
    @Override public String getStatus() { return "OPEN"; }
    @Override public Date getUpdateDate() { return UPDATED; }
  }

  static final class FileInput implements Input<Issue> {
    final LineHashSequence lineHashes;
    final BlockHashSequence blockHashes;
    final List<Issue> issues = new ArrayList<>();

    FileInput(List<String> lines) {
      this.lineHashes = LineHashSequence.createForLines(lines);
      this.blockHashes = BlockHashSequence.create(lineHashes);
    }

    @Override public LineHashSequence getLineHashSequence() { return lineHashes; }
    @Override public BlockHashSequence getBlockHashSequence() { return blockHashes; }
    @Override public Collection<Issue> getIssues() { return issues; }
  }

  private static String decode(String token) {
    return new String(Base64.getDecoder().decode(token), StandardCharsets.UTF_8);
  }

  private static List<String> readLines(BufferedReader in, String tag) throws Exception {
    String[] head = in.readLine().split(" ");
    if (!head[0].equals(tag)) throw new IllegalStateException("expected " + tag);
    List<String> out = new ArrayList<>();
    for (int i = 0; i < Integer.parseInt(head[1]); i++) out.add(decode(in.readLine()));
    return out;
  }

  private static void readIssues(BufferedReader in, String tag, FileInput input) throws Exception {
    String[] head = in.readLine().split(" ");
    if (!head[0].equals(tag)) throw new IllegalStateException("expected " + tag);
    for (int i = 0; i < Integer.parseInt(head[1]); i++) {
      String[] f = in.readLine().split(" ", -1);
      input.issues.add(new Issue(decode(f[0]), Integer.parseInt(f[1]), decode(f[2]), input.lineHashes));
    }
  }

  public static void main(String[] args) throws Exception {
    BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
    String tag;
    while ((tag = in.readLine()) != null) {
      if (tag.isEmpty()) continue;
      if (tag.startsWith("ORDER")) {
        Multimap<Integer, Integer> map = ArrayListMultimap.create();
        String[] parts = (tag.substring(5) + " ").split("\\|", -1);
        for (String key : parts[0].trim().split(" +")) {
          if (!key.isEmpty()) map.put(Integer.parseInt(key), 0);
        }
        if (parts.length > 1) {
          for (String key : parts[1].trim().split(" +")) {
            if (!key.isEmpty()) map.removeAll(Integer.parseInt(key));
          }
        }
        StringJoiner order = new StringJoiner(" ");
        for (Integer key : map.keySet()) order.add(key.toString());
        System.out.println(order);
        continue;
      }
      if (!tag.equals("CASE")) throw new IllegalStateException("expected CASE");
      FileInput base = new FileInput(readLines(in, "OLD"));
      FileInput raw = new FileInput(readLines(in, "NEW"));
      readIssues(in, "BASE", base);
      readIssues(in, "RAW", raw);
      if (!in.readLine().equals("END")) throw new IllegalStateException("expected END");

      NonClosedTracking<Issue, Issue> tracking = new Tracker<Issue, Issue>().trackNonClosed(raw, base);
      Map<Issue, Integer> baseIndex = new IdentityHashMap<>();
      for (int i = 0; i < base.issues.size(); i++) baseIndex.put(base.issues.get(i), i);
      StringJoiner line = new StringJoiner(" ");
      for (Issue r : raw.issues) {
        Issue b = tracking.baseFor(r);
        line.add(String.valueOf(b == null ? -1 : baseIndex.get(b)));
      }
      System.out.println(line);
    }
  }
}
