// Loads a browser <script> file in a CommonJS sandbox and returns its
// module.exports. Independent of any package.json "type" up the tree (no Node
// module resolution involved). The browser files carry a dual-export tail:
//   if (typeof module !== "undefined" && module.exports) module.exports = ...;
// which runs here (module is provided) and is skipped in a real browser.
const fs = require("fs");
const path = require("path");

function loadScript(relFromRepoRoot) {
  const abs = path.join(__dirname, "..", "..", "..", relFromRepoRoot);
  const code = fs.readFileSync(abs, "utf8");
  const module = { exports: {} };
  new Function("module", "exports", code)(module, module.exports);
  return module.exports;
}

module.exports = { loadScript };
