const COMMENT = /^\s*#/;
for (const line of lines) {
  if (COMMENT.test(line)) continue;
  if (new RegExp(userPattern).test(line)) count++;
}
