const _ = require("lodash");

app.post("/settings", (req, res) => {
  _.merge(userSettings, req.body);
  $.extend(true, defaults, req.body.prefs);
});
