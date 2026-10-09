app.get("/login/done", (req, res) => {
  res.redirect(req.query.next);
});

app.post("/go", (req, res) => res.redirect(302, req.body.url));

const target = new URLSearchParams(location.search).get("return");
location.href = new URLSearchParams(location.search).get("return");
