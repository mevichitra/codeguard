import fs from "fs";
import path from "path";

app.get("/file", (req, res) => {
  const data = fs.readFileSync(path.join(__dirname, "files", req.query.name as string));
  res.send(data);
});

app.get("/download/:name", (req, res) => {
  res.download(`/srv/files/${req.params.name}`);
});

app.delete("/upload", async (req, res) => {
  await fs.promises.unlink("/tmp/" + req.body.file);
});
