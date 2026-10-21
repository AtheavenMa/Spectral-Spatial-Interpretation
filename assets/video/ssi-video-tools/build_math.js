// Typeset every on-screen math symbol with MathJax (TeX input -> self-contained SVG paths).
// fontCache:'none' inlines glyph paths so each SVG renders identically with no font files.
"use strict";
const fs = require("fs");
const { mathjax } = require("mathjax-full/js/mathjax.js");
const { TeX } = require("mathjax-full/js/input/tex.js");
const { SVG } = require("mathjax-full/js/output/svg.js");
const { liteAdaptor } = require("mathjax-full/js/adaptors/liteAdaptor.js");
const { RegisterHTMLHandler } = require("mathjax-full/js/handlers/html.js");

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const doc = mathjax.document("", {
  InputJax: new TeX({ packages: ["base"] }),
  OutputJax: new SVG({ fontCache: "none" }),
});

const FORMULAS = {
  phi: "\\Phi(g,c)",
  dfx: "\\Delta f",
  fx: "f(x)",
  g: "g",
  c: "c",
  c1: "c_1",
  c2: "c_2",
  c3: "c_3",
  c4: "c_4",
  c5: "c_5",
  c6: "c_6",
  maskeq: "x_{g,c}\\;\\to\\;\\bar{x}_{c}",
};

const out = {};
for (const [key, tex] of Object.entries(FORMULAS)) {
  const node = doc.convert(tex, { display: false });
  let svg = adaptor.innerHTML(node);
  const vb = svg.match(/viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"/);
  if (!vb) throw new Error("no viewBox for " + key);
  const [x, y, w, h] = vb.slice(1).map(Number);
  // strip MathJax's ex-based sizing; the page sizes each formula in px from the viewBox
  svg = svg
    .replace(/ width="[^"]*"/, "")
    .replace(/ height="[^"]*"/, "")
    .replace(/ style="[^"]*"/, "")
    .replace(/ role="img"/, "")
    .replace(/ focusable="false"/, "");
  out[key] = { tex, svg, vb: [x, y, w, h] };
}
fs.writeFileSync(process.argv[2], "window.SSI_MATH = " + JSON.stringify(out) + ";\n");
for (const [k, v] of Object.entries(out)) console.log(k, v.tex, v.vb.join(" "), v.svg.length + " chars");
