/**
 * Demo 1: Developer Inner-Loop - TypeScript Service & Component
 * Demonstrates Tree-sitter AST analysis detecting frontend & Node.js anti-patterns.
 */

import * as cp from "child_process";
import * as React from "react";

// CG-SEC-105: Hardcoded sensitive secret
const apiKey = "sk-live-super-secret-12345";

export function checkoutBranch(branchName: string): string {
  // CG-SEC-102: Shell injection in Node.js child_process
  return cp.execSync("git checkout " + branchName).toString();
}

export function generatePasswordResetToken(): string {
  // CG-SEC-106: Cryptographically weak PRNG used for security token
  const resetToken = "token-" + Math.random().toString(36).substring(2);
  return resetToken;
}

export function executeDynamicScript(userCode: string): any {
  // CG-SEC-101: Arbitrary dynamic code execution
  return eval(userCode);
}

export function renderUserBio(container: HTMLElement, bioMarkdown: string): void {
  // CG-SEC-103: DOM Cross-Site Scripting (XSS) sink
  container.innerHTML = bioMarkdown;
}

export function CommentPreview({ markdownHtml }: { markdownHtml: string }) {
  // CG-SEC-104: React XSS vector via dangerouslySetInnerHTML
  return <div dangerouslySetInnerHTML={{ __html: markdownHtml }} />;
}
