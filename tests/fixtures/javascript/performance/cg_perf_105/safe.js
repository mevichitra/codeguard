const SOURCE = new Set(["js", "jsx", "ts", "tsx"]);
for (const file of files) {
  if (SOURCE.has(file.ext)) total++;
  if (["a", "b"].includes(file.ext)) total++;
}
if (["js", "jsx", "ts", "tsx"].includes(mode)) total++;
