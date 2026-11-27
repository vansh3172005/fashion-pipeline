// Outfit recommender tests (outfit_styling_rules.md). Run: node tests/test_recommend.js
const assert = require("assert");
const path = require("path");
const R = require(path.join(__dirname, "..", "web", "recommend.js"));

let n = 0;
const test = (name, fn) => { fn(); n++; console.log("ok -", name); };
const item = (id, category, department, o = {}) => ({
  id, category, department, title: id, gender: "men", occasion: "casual",
  attr_source: {occasion: "tags"}, primary_style: "minimalist", price_band: "affordable", ...o});

test("section 2: gender, occasion and style must match", () => {
  const a = item("a", "shirt", "topwear");
  assert.ok(R.pairOk(a, item("b", "jeans", "bottomwear")));
  assert.ok(!R.pairOk(a, item("c", "jeans", "bottomwear", {gender: "women"})));
  assert.ok(R.pairOk(a, item("d", "jeans", "bottomwear", {gender: "unisex"})));
  assert.ok(!R.pairOk(a, item("e", "jeans", "bottomwear", {occasion: "festive"})));
  assert.ok(R.pairOk(a, item("f", "jeans", "bottomwear", {occasion: "festive", attr_source: {occasion: "default"}})));
  assert.ok(R.pairOk(a, item("g", "jeans", "bottomwear", {primary_style: "classic"})));
  assert.ok(!R.pairOk(a, item("h", "jeans", "bottomwear", {primary_style: "glam"})));
});

test("section 2: size in stock (letters, and waist sizes for bottoms)", () => {
  assert.ok(R.sizeOk(item("a", "shirt", "topwear", {sizes_available: ["S", "M"]}), "M"));
  assert.ok(!R.sizeOk(item("b", "shirt", "topwear", {sizes_available: ["S"]}), "M"));
  assert.ok(R.sizeOk(item("c", "jeans", "bottomwear", {sizes_available: ["30", "32"]}), "M"));
  assert.ok(R.sizeOk(item("d", "shoes", "footwear", {sizes_available: ["8"]}), "M"));
});

test("sections 3-7: colour, pattern, fit, fabric and price are scored", () => {
  const good = R.score([item("a", "shirt", "topwear", {color: "navy", pattern: "solid", fit: "oversized"}),
                        item("b", "jeans", "bottomwear", {color: "white", pattern: "solid", fit: "slim"})]);
  assert.strictEqual(good.score, good.max);
  assert.ok(good.why.includes("navy + white"));
  const bad = R.score([item("a", "shirt", "topwear", {color: "red", pattern: "printed", fit: "oversized", price_band: "cheap"}),
                       item("b", "jeans", "bottomwear", {color: "green", pattern: "checked", fit: "baggy", price_band: "luxury"})]);
  assert.ok(bad.score < bad.max - 2);
});

test("section 1 + 8: a full outfit is built around a piece", () => {
  const cat = [item("top", "shirt", "topwear", {color: "white"}), item("j", "jeans", "bottomwear", {color: "navy"}),
               item("s", "shoes", "footwear", {color: "white"}), item("w", "watch", "accessories", {color: "black"}),
               item("x", "jeans", "bottomwear", {color: "red", gender: "women"})];
  const o = R.completeLook(cat[0], cat, {n: 3});
  assert.strictEqual(o.length, 1);
  assert.deepStrictEqual(o[0].items.map(i => i.id).sort(), ["j", "s", "top", "w"]);
});

test("mis-labelled pieces (e.g. a handkerchief filed as shoes) are never suggested", () => {
  const cat = [item("top", "shirt", "topwear"), item("j", "jeans", "bottomwear"),
               item("h", "shoes", "footwear", {title: "Cotton Handkerchief"})];
  assert.strictEqual(R.completeLook(cat[0], cat).length, 0);
});

test("real catalogues: every style gets outfits", () => {
  for (const f of ["catalogue.json", "catalogue_women.json"]) {
    const cat = require(path.join(__dirname, "..", "web", f));
    const styles = [...new Set(cat.map(i => i.primary_style))].filter(s => s !== "unclassified");
    for (const s of styles) assert.ok(R.buildOutfits(cat, {style: s}, 3).length > 0, `${f} ${s}`);
  }
});

console.log(`${n} tests passed`);
