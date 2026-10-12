// SPDX-License-Identifier: Apache-2.0

/**
 * Convert a 1-indexed UTF-8 byte column (what CodeGuard reports) to a 0-indexed
 * UTF-16 character offset within `lineText` (what VS Code positions use).
 */
export function byteColumnToCharacter(lineText: string, byteCol: number): number {
  const target = Math.max(byteCol - 1, 0);
  let bytes = 0;
  let character = 0;
  for (const ch of lineText) {
    if (bytes >= target) {
      return character;
    }
    bytes += Buffer.byteLength(ch, "utf8");
    character += ch.length;
  }
  return character + Math.max(target - bytes, 0);
}
