const _ = require("lodash");

app.post("/settings", (req, res) => {
  Object.assign(userSettings, { theme: req.body.theme });
  _.merge(userSettings, defaults);
  $.extend(defaults, req.body);
});
