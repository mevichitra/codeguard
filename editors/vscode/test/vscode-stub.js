// Minimal stand-in for the `vscode` module so pure extension logic can run under node:test.
"use strict";
const Module = require("module");

class EventEmitter {
  constructor() { this.listeners = []; this.event = (fn) => { this.listeners.push(fn); return { dispose() {} }; }; }
  fire(value) { for (const fn of this.listeners) fn(value); }
  dispose() { this.listeners = []; }
}
class ThemeColor { constructor(id) { this.id = id; } }
class ThemeIcon { constructor(id, color) { this.id = id; this.color = color; } }
ThemeIcon.File = new ThemeIcon("file");
class MarkdownString {
  constructor(value = "", supportThemeIcons = false) { this.value = value; this.supportThemeIcons = supportThemeIcons; }
  appendMarkdown(text) { this.value += text; return this; }
}
const TreeItemCollapsibleState = { None: 0, Collapsed: 1, Expanded: 2 };
class TreeItem {
  constructor(labelOrUri, collapsibleState) {
    if (typeof labelOrUri === "string") this.label = labelOrUri; else this.resourceUri = labelOrUri;
    this.collapsibleState = collapsibleState;
  }
}
const Uri = {
  parse: (value) => ({ scheme: value.split(":")[0], toString: () => value, fsPath: value.replace(/^file:\/\//, "") }),
  joinPath: (base, ...parts) => Uri.parse(`${base.toString()}/${parts.join("/")}`),
};

const vscode = { EventEmitter, ThemeColor, ThemeIcon, MarkdownString, TreeItem, TreeItemCollapsibleState, Uri };

const original = Module._load;
Module._load = function (request, parent, isMain) {
  if (request === "vscode") return vscode;
  return original.call(this, request, parent, isMain);
};

module.exports = vscode;
