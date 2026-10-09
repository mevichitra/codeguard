// SPDX-License-Identifier: Apache-2.0
// Wire types of CodeGuard's custom LSP requests. No runtime dependencies, so they
// can be imported by views and by unit tests without loading the language client.

export type Severity = "critical" | "high" | "medium" | "low" | "info";
export const SEVERITIES: Severity[] = ["critical", "high", "medium", "low", "info"];

export interface SummaryCounts {
  total: number;
  bySeverity: Record<Severity, number>;
  byCategory: Record<string, number>;
  fixable: number;
  suppressed: number;
  baselined: number;
  files: number;
}

export interface SummaryFinding {
  ruleId: string;
  title: string;
  description: string;
  severity: Severity;
  category: string;
  line: number;
  col: number;
  endLine: number | null;
  endCol: number | null;
  fingerprint: string;
  hasFix: boolean;
  cwe: string | null;
  helpUri: string;
  confidence: number;
}

export interface SummaryFile {
  uri: string;
  path: string;
  counts: { total: number; bySeverity: Record<Severity, number> };
  findings: SummaryFinding[];
}

export interface SummaryRule {
  id: string;
  title: string;
  severity: Severity;
  category: string;
  count: number;
  hasFix: boolean;
}

export interface Summary {
  schemaVersion: number;
  generatedAt: string;
  workspaceRoot: string;
  counts: SummaryCounts;
  files: SummaryFile[];
  rules: SummaryRule[];
}
