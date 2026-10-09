// Unit tests for the extension's pure logic: run with `npm test` after `npm run compile`.
"use strict";
require("./vscode-stub");
const test = require("node:test");
const assert = require("node:assert/strict");
const { FindingsProvider } = require("../out/findingsView");
const { renderOverview, escapeHtml } = require("../out/overview");
const { byteColumnToCharacter } = require("../out/text");

function memento() {
  const store = new Map();
  return { get: (k, d) => (store.has(k) ? store.get(k) : d), update: async (k, v) => store.set(k, v) };
}

function finding(overrides) {
  return {
    ruleId: "CG-SEC-011", title: "Untrusted input reaches a shell command", description: "d",
    severity: "critical", category: "security", line: 6, col: 5, endLine: 6, endCol: 20,
    fingerprint: "fp1", hasFix: false, cwe: "CWE-78", helpUri: "https://example/CG-SEC-011/", confidence: 0.85,
    ...overrides,
  };
}

const zero = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
const SUMMARY = {
  schemaVersion: 1,
  generatedAt: "2026-10-09T10:00:00Z",
  workspaceRoot: "/repo",
  counts: { total: 3, bySeverity: { ...zero, critical: 1, low: 1, info: 1 }, byCategory: { security: 1, performance: 2 }, fixable: 1, suppressed: 0, baselined: 0, files: 2 },
  files: [
    { uri: "file:///repo/app.py", path: "app.py", counts: { total: 1, bySeverity: { ...zero, critical: 1 } }, findings: [finding({})] },
    {
      uri: "file:///repo/lib/m.py", path: "lib/m.py", counts: { total: 2, bySeverity: { ...zero, low: 1, info: 1 } },
      findings: [
        finding({ ruleId: "CG-PERF-001", severity: "low", category: "performance", fingerprint: "fp2", hasFix: true, line: 3 }),
        finding({ ruleId: "CG-PERF-004", severity: "info", category: "performance", fingerprint: "fp3", hasFix: true, line: 9 }),
      ],
    },
  ],
  rules: [{ id: "CG-PERF-001", title: "<b>x</b>", severity: "low", category: "performance", count: 1, hasFix: true }],
};

test("groups by severity, then file, then finding", () => {
  const p = new FindingsProvider(memento());
  p.update(SUMMARY);
  const groups = p.getChildren();
  assert.deepEqual(groups.map((g) => g.label), ["Critical", "Low", "Info"]);
  const files = p.getChildren(groups[0]);
  assert.equal(files.length, 1);
  assert.equal(files[0].file.path, "app.py");
  const [leaf] = p.getChildren(files[0]);
  const item = p.getTreeItem(leaf);
  assert.equal(item.label, "Untrusted input reaches a shell command");
  assert.equal(item.description, "CG-SEC-011 · Ln 6");
  assert.equal(item.contextValue, "finding");
  assert.equal(item.iconPath.id, "flame");
  assert.deepEqual(item.command.arguments[0], { uri: "file:///repo/app.py", finding: SUMMARY.files[0].findings[0] });
});

test("fixable findings advertise it and get the fixable context value", () => {
  const p = new FindingsProvider(memento());
  p.update(SUMMARY);
  p.setGrouping("file");
  const files = p.getChildren();
  assert.deepEqual(files.map((f) => f.file.path), ["app.py", "lib/m.py"]); // worst severity first
  const leaves = p.getChildren(files[1]).map((n) => p.getTreeItem(n));
  assert.equal(leaves[0].contextValue, "finding.fixable");
  assert.match(leaves[0].description, /fixable$/);
});

test("category grouping puts security first and uses friendly labels", () => {
  const p = new FindingsProvider(memento());
  p.update(SUMMARY);
  p.setGrouping("category");
  assert.deepEqual(p.getChildren().map((g) => g.label), ["Security", "Performance"]);
});

test("severity filter hides findings and is remembered", () => {
  const store = memento();
  const p = new FindingsProvider(store);
  p.update(SUMMARY);
  p.setSeverities(["critical", "high"]);
  assert.deepEqual(p.stats(), { total: 3, visible: 1 });
  const again = new FindingsProvider(store);
  assert.deepEqual(again.visibleSeverities, ["critical", "high"]);
});

test("empty or missing summary yields no nodes (welcome view shows)", () => {
  const p = new FindingsProvider(memento());
  assert.deepEqual(p.getChildren(), []);
});

test("overview escapes untrusted text and locks scripts to a nonce", () => {
  const evil = structuredClone(SUMMARY);
  evil.files[0].path = '<img src=x onerror="alert(1)">';
  const html = renderOverview(evil, "vscode-resource:");
  assert.ok(!html.includes('<img src=x onerror="alert(1)">'));
  assert.ok(html.includes("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"));
  assert.ok(html.includes("&lt;b&gt;x&lt;/b&gt;"));
  const nonce = /script-src 'nonce-([^']+)'/.exec(html)[1];
  assert.ok(html.includes(`<script nonce="${nonce}">`));
  assert.match(html, /Fix 1 safe issue</);
  assert.equal(escapeHtml(`"'&`), "&quot;&#39;&amp;");
});

test("overview before the first scan", () => {
  assert.match(renderOverview(undefined, "x"), /Waiting for the first scan/);
});

test("byte columns map to UTF-16 characters", () => {
  const line = 'x = "é😀" + y';
  const yByte = Buffer.byteLength(line.slice(0, line.indexOf("y")), "utf8") + 1;
  assert.equal(byteColumnToCharacter(line, yByte), line.indexOf("y"));
  assert.equal(byteColumnToCharacter("abc", 1), 0);
  assert.equal(byteColumnToCharacter("", 4), 3);
});
