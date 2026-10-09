import fs from "fs";
import path from "path";

app.get("/file", (req, res) => {
  const data = fs.readFileSync(path.join(__dirname, "files", path.basename(req.query.name as string)));
  res.sendFile(req.params.name, { root: "/srv/files" });
  fs.readFileSync("/etc/app/config.json");
});
