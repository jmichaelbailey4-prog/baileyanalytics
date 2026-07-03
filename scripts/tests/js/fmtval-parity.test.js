/* The five fmtVal/_fmt twins (build.py, lens.js, predict.js, scoring.js,
   track-record.js) must agree. This test extracts each JS implementation from
   its source file and runs all of them over the shared golden battery; the
   Python side runs the SAME battery in test_build.py (TestFmtParityGoldens).
   Change one twin without the others and one of the two suites goes red. */
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const DASH = path.join(__dirname, "..", "..", "..", "dashboards");

function extractFmtVal(file) {
  const src = fs.readFileSync(path.join(DASH, file), "utf8");
  const m = src.match(/function fmtVal\([\s\S]*?\n  \}/);
  assert.ok(m, `fmtVal not found in ${file}`);
  return new Function("return " + m[0])();
}

// Keep in sync with scripts/tests/test_build.py TestFmtParityGoldens.
const GOLDENS = [
  [2578.5, "Bcf", "thousands", "2,579 Bcf"],   // half-up, the drift case
  [0.5, "", "thousands", "1"],
  [-55.9, "$B", "decimal", "-$55.90B"],
  [2.4, "$T", "decimal", "$2.40T"],
  [4.153, "$", "decimal", "$4.15"],
  [9.4, "months", "decimal", "9.40 months"],
  [4.17, "M", "decimal", "4.17M"],
  [215000, "", "thousands", "215,000"],
  [-1.234, "%", "decimal", "-1.23%"],
  [1.77, "σ", "decimal", "1.77σ"],
  [7483.24, "", "thousands", "7,483"],
];

for (const file of ["lens.js", "predict.js", "scoring.js", "track-record.js"]) {
  test(`fmtVal goldens — ${file}`, () => {
    const fmtVal = extractFmtVal(file);
    for (const [v, unit, vf, want] of GOLDENS) {
      assert.strictEqual(fmtVal(v, unit, vf), want,
        `${file}: fmtVal(${v}, ${JSON.stringify(unit)}, ${vf})`);
    }
  });
}
