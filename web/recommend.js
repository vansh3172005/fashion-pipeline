/* Outfit recommender: implements outfit_styling_rules.md.
 *
 *   section 1  outfit templates (Western, One-piece, Indian, Co-ord)
 *   section 2  hard rules: gender, occasion family, compatible styles, size in stock
 *   sections 3-7  soft rules, +1 each: colour (two checks), pattern, fit, fabric, price
 *   section 8  keep passing outfits, rank by score, vary the items, give one reason
 *
 * Runs in the browser (window.Recommender) and in Node for tests (module.exports).
 * Everything is computed from the catalogue item fields; nothing leaves the PC.
 */
(function (root) {
  "use strict";

  // ---------------------------------------------------------------- section 1: pieces
  const TOP = new Set(["tshirt", "shirt", "polo", "top", "sweatshirt", "hoodie", "sweater"]);
  const BOTTOM = new Set(["jeans", "trousers", "joggers", "shorts", "skirt", "leggings"]);
  const LAYER = new Set(["jacket", "blazer", "shrug"]);
  const ONE_PIECE = new Set(["dress", "gown", "jumpsuit"]);
  const COORD = new Set(["coord_set"]);
  const INDIAN_TOP = new Set(["kurta"]);
  const INDIAN_BOTTOM = new Set(["pyjama", "dhoti", "ethnic_bottom", "trousers", "leggings"]);
  const INDIAN_FULL = new Set(["kurta_set", "sherwani", "saree", "lehenga"]);
  const INDIAN_LAYER = new Set(["ethnic_jacket", "shrug"]);
  const FOOTWEAR = new Set(["shoes", "sandals", "heels", "flats", "ethnic_footwear"]);
  const ETHNIC_FOOTWEAR = new Set(["ethnic_footwear", "sandals", "flats", "heels"]);
  const ACCESSORY = new Set(["belt", "bag", "cap", "sunglasses", "watch", "jewellery", "wallet",
                             "hair_accessory", "clutch", "tie", "scarf"]);
  const ETHNIC_ACCESSORY = new Set(["scarf", "jewellery", "clutch", "ethnic_accessory", "bag"]);

  // which template an item anchors, and the slots it needs
  function templateOf(it) {
    const c = it.category;
    if (ONE_PIECE.has(c)) return "onepiece";
    if (COORD.has(c)) return "coord";
    if (INDIAN_FULL.has(c) || INDIAN_TOP.has(c) || c === "ethnic_bottom" || c === "pyjama" ||
        c === "dhoti" || c === "blouse" || c === "ethnic_jacket") return "indian";
    if (TOP.has(c) || BOTTOM.has(c) || LAYER.has(c)) return "western";
    if (it.department === "footwear" || it.department === "accessories") return "accessory";
    return null;
  }
  const SLOTS = {
    western: [["top", TOP], ["bottom", BOTTOM], ["footwear", FOOTWEAR], ["accessory", ACCESSORY],
              ["layer", LAYER]],
    onepiece: [["main", ONE_PIECE], ["footwear", FOOTWEAR], ["accessory", ACCESSORY]],
    coord: [["main", COORD], ["footwear", FOOTWEAR], ["accessory", ACCESSORY]],
    indian_full: [["main", INDIAN_FULL], ["footwear", ETHNIC_FOOTWEAR], ["accessory", ETHNIC_ACCESSORY],
                  ["layer", INDIAN_LAYER]],
    indian_kurta: [["top", INDIAN_TOP], ["bottom", INDIAN_BOTTOM], ["footwear", ETHNIC_FOOTWEAR],
                   ["accessory", ETHNIC_ACCESSORY], ["layer", INDIAN_LAYER]],
  };
  const OPTIONAL = new Set(["accessory", "layer"]);

  // ---------------------------------------------------------------- section 2: hard rules
  const OCCASION_FAMILY = {
    casual: "casual", street: "casual", college: "casual", vacation: "casual", lounge: "casual",
    formal: "formal", "smart casual": "formal", party: "party", festive: "festive",
    activewear: "active",
  };
  function occasionFamily(it) {
    // an occasion the pipeline only defaulted ("casual" with no evidence) fits any outfit
    if ((it.attr_source || {}).occasion === "default") return null;
    return OCCASION_FAMILY[it.occasion] || null;
  }
  const STYLE_PAIRS = {
    minimalist: ["classic", "streetwear", "sporty"],
    classic: ["minimalist", "glam"],
    streetwear: ["minimalist", "sporty", "edgy"],
    boho: ["ethnic_fusion", "minimalist"],
    sporty: ["streetwear", "minimalist"],
    glam: ["classic", "traditional", "edgy"],
    ethnic_fusion: ["traditional", "boho", "glam"],
    traditional: ["ethnic_fusion", "glam"],
    edgy: ["streetwear", "glam"],
  };
  function stylesOk(a, b) {
    const sa = a.primary_style, sb = b.primary_style;
    if (!sa || !sb || sa === "unclassified" || sb === "unclassified" || sa === sb) return true;
    return (STYLE_PAIRS[sa] || []).includes(sb) || (STYLE_PAIRS[sb] || []).includes(sa);
  }
  function genderOk(a, b) {
    return a.gender === b.gender || a.gender === "unisex" || b.gender === "unisex";
  }
  function occasionOk(a, b) {
    const fa = occasionFamily(a), fb = occasionFamily(b);
    return !fa || !fb || fa === fb;
  }
  function sizeOk(it, size) {
    if (!size || it.department === "footwear" || it.department === "accessories") return true;
    const s = (it.sizes_available || []).map(x => String(x).toUpperCase());
    if (!s.length) return true;  // free size / one size
    const want = String(size).toUpperCase();
    // bottoms are often sold by waist: S 28-30, M 32, L 34, XL 36, XXL 38
    const waist = {XS: ["26", "28"], S: ["28", "30"], M: ["32"], L: ["34"], XL: ["36"], XXL: ["38"], "2XL": ["38"]}[want] || [];
    return s.some(x => { const parts = x.split(/[^A-Z0-9]+/);
      return x === want || parts.includes(want) || waist.some(w => parts.includes(w)); });
  }
  // an item with no real occasion tag suits the occasions its style is worn for
  const STYLE_OCCASIONS = {
    casual: null,  // every style
    formal: ["classic", "minimalist", "glam"],
    party: ["glam", "edgy", "classic", "minimalist", "streetwear", "ethnic_fusion"],
    festive: ["traditional", "ethnic_fusion", "glam", "boho"],
    active: ["sporty", "streetwear"],
  };
  function suitsOccasion(it, occ) {
    if (!occ) return true;
    const fam = occasionFamily(it);
    if (fam) return fam === occ;
    const ok = STYLE_OCCASIONS[occ];
    return !ok || ok.includes(it.primary_style);
  }
  function pairOk(a, b) { return genderOk(a, b) && occasionOk(a, b) && stylesOk(a, b); }
  // a footwear, accessory or layer pick whose title names another kind of item is a
  // catalogue mis-label ("Cotton Handkerchief" filed as shoes): never suggest it
  const NOT_FOR = {
    footwear: /\b(handkerchief|socks?|pocket square|polish|laces?|insoles?|t-?shirts?|shirts?|kurtas?)\b/i,
    accessory: /\b(jeans|denim pants|trousers?|t-?shirts?|shirts?|kurtas?|dress|shorts|joggers?)\b/i,
    layer: /\b(t-?shirts?|tees?|polos?|kurtas?|dress)\b/i,
  };
  function titleOk(slot, it) {
    const re = NOT_FOR[slot];
    if (!re || !re.test(it.title || "")) return true;
    return slot === "layer" && /\b(jacket|shacket|overshirt|blazer|shrug|cardigan|koti|bundi)\b/i.test(it.title);
  }

  // ---------------------------------------------------------------- sections 3-7: soft rules
  const NEUTRAL = new Set(["black", "white", "grey", "navy", "beige"]);
  const SAFE_PAIRS = [["navy", "white"], ["black", "white"], ["beige", "white"], ["green", "beige"],
                      ["blue", "white"], ["red", "beige"], ["black", "red"], ["pink", "white"]];
  const CLASH = [["red", "green"], ["orange", "pink"], ["purple", "yellow"]];
  const PATTERNED = new Set(["printed", "graphic", "floral", "striped", "checked", "embroidered",
                             "embellished", "ethnic print", "animal print", "polka dot", "tie dye",
                             "camouflage", "colour block"]);
  const LOOSE = new Set(["oversized", "relaxed", "boxy", "wide leg", "flared"]);
  const SLIM = new Set(["slim", "skinny", "straight", "regular", "tapered", "cropped"]);
  const LIGHT = new Set(["cotton", "linen", "muslin", "chiffon", "georgette"]);
  const HEAVY = new Set(["wool", "fleece", "velvet", "corduroy", "cashmere"]);
  const FESTIVE_FABRIC = new Set(["silk", "velvet", "brocade", "tissue", "organza"]);
  const BANDS = ["cheap", "affordable", "luxury"];
  const has = (list, x, y) => list.some(([p, q]) => (p === x && q === y) || (p === y && q === x));

  function garments(items) {
    return items.filter(i => i.department !== "footwear" && i.department !== "accessories");
  }
  function score(items) {
    const g = garments(items);
    const cols = [...new Set(items.map(i => i.color).filter(Boolean))];
    const bright = cols.filter(c => !NEUTRAL.has(c) && c !== "multi");
    const checks = [], why = [];
    // 3. colour: at most two non-neutral colours, no clash; a safe pair or one colour family
    const noClash = !bright.some((x, i) => bright.slice(i + 1).some(y => has(CLASH, x, y)));
    checks.push(bright.length <= 2 && noClash);
    const gc = [...new Set(g.map(i => i.color).filter(Boolean))];
    const pairFound = gc.some((x, i) => gc.slice(i + 1).some(y => has(SAFE_PAIRS, x, y)));
    const tonal = (gc.length === 1 && gc[0] !== "multi") || (gc.length > 0 && gc.every(c => NEUTRAL.has(c)));
    checks.push(pairFound || tonal);
    if (pairFound) {
      const p = SAFE_PAIRS.find(([x, y]) => gc.includes(x) && gc.includes(y));
      why.push(`${p[0]} + ${p[1]}`);
    } else if (tonal) why.push(gc.length === 1 ? `all ${gc[0]}` : "all neutrals");
    // 4. pattern: one patterned garment at most
    const pat = g.filter(i => PATTERNED.has(i.pattern)).length;
    checks.push(pat <= 1);
    if (pat === 1) why.push("one patterned piece"); else if (!pat) why.push("all solid");
    // 5. fit: balance a loose piece with a slim one; no oversized on oversized (unless streetwear)
    const top = g.find(i => TOP.has(i.category) || INDIAN_TOP.has(i.category));
    const bot = g.find(i => BOTTOM.has(i.category) || INDIAN_BOTTOM.has(i.category));
    let fitOk = true;
    if (top && bot && top.fit && bot.fit) {
      const both = LOOSE.has(top.fit) && LOOSE.has(bot.fit);
      fitOk = !both || (top.primary_style === "streetwear" && bot.primary_style === "streetwear");
      if (fitOk && LOOSE.has(top.fit) !== LOOSE.has(bot.fit)) why.push("balanced fit");
    }
    checks.push(fitOk);
    // 6. fabric and season: light with light, heavy with heavy; no festive fabric with gym wear
    const fab = new Set(g.flatMap(i => i.fabrics || (i.fabric ? [i.fabric] : [])));
    const mixed = [...fab].some(f => LIGHT.has(f)) && [...fab].some(f => HEAVY.has(f));
    const gym = items.some(i => occasionFamily(i) === "active");
    checks.push(!mixed && !(gym && [...fab].some(f => FESTIVE_FABRIC.has(f))));
    // 7. price: same or neighbouring band
    const bands = items.map(i => BANDS.indexOf(i.price_band)).filter(b => b >= 0);
    checks.push(!bands.length || Math.max(...bands) - Math.min(...bands) <= 1);
    const fam = items.map(occasionFamily).find(Boolean);
    if (fam) why.push(fam === "active" ? "activewear" : fam);
    return {score: checks.filter(Boolean).length, max: checks.length, why: why.slice(0, 3).join(", ")};
  }

  // ---------------------------------------------------------------- section 8: build and rank
  function slotsFor(anchor) {
    const t = templateOf(anchor);
    if (t === "indian") return INDIAN_FULL.has(anchor.category) ? SLOTS.indian_full : SLOTS.indian_kurta;
    return SLOTS[t] || null;
  }
  function slotOf(slots, it) {
    const s = slots.find(([, set]) => set.has(it.category));
    return s ? s[0] : null;
  }
  const INDEX = new WeakMap();
  function indexOf(catalogue) {
    let m = INDEX.get(catalogue);
    if (!m) {
      m = new Map();
      for (const it of catalogue) { if (!m.has(it.category)) m.set(it.category, []); m.get(it.category).push(it); }
      INDEX.set(catalogue, m);
    }
    return m;
  }
  function hash(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619); return h >>> 0; }

  /** Up to ``n`` outfits built around ``anchor`` from ``catalogue``.
   *  opts: {size, n, seed, beam} */
  function completeLook(anchor, catalogue, opts = {}) {
    const slots = slotsFor(anchor);
    if (!slots) return [];
    const n = opts.n || 3, beam = opts.beam || 14, seed = opts.seed || 0;
    const mySlot = slotOf(slots, anchor);
    if (!mySlot) return [];
    // candidates per slot: pass the hard rules against the anchor, ranked by the soft
    // score of the pair, with a seeded tie-break so "more" gives other suggestions
    const cand = {}, byCat = indexOf(catalogue);
    for (const [name, set] of slots) {
      if (name === mySlot) continue;
      const list = [];
      for (const it of [...set].flatMap(c => byCat.get(c) || [])) {
        if (it.id === anchor.id || (opts.exclude && opts.exclude.has(it.id)) ||
            (opts.exclude && opts.exclude.has("^" + it.id)) || !pairOk(anchor, it) || !sizeOk(it, opts.size)) continue;
        if (name === "bottom" && templateOf(anchor) === "indian" && it.category === "trousers" &&
            anchor.gender !== "women") continue;  // men: kurta with pyjama / dhoti, not trousers
        if (!titleOk(name, it)) continue;
        const sameStyle = it.primary_style === anchor.primary_style ? 2 :
          (it.primary_style && it.primary_style !== "unclassified" ? 1 : 0);
        const conf = {high: 2, medium: 1}[it.style_confidence] || 0;
        list.push([score([anchor, it]).score, sameStyle + conf, hash(it.id + seed), it]);
      }
      list.sort((a, b) => b[0] - a[0] || b[1] - a[1] || a[2] - b[2]);
      cand[name] = list.slice(0, beam).map(x => x[3]);
    }
    const need = slots.map(([s]) => s).filter(s => s !== mySlot && !OPTIONAL.has(s));
    if (need.some(s => !cand[s] || !cand[s].length)) return [];
    // combine required slots, then add the best optional pieces that still pass the rules
    let outfits = [[anchor]];
    for (const s of need) {
      const next = [];
      for (const o of outfits) for (const it of cand[s]) if (o.every(x => pairOk(x, it))) next.push([...o, it]);
      next.sort((a, b) => score(b).score - score(a).score);
      outfits = next.slice(0, 60);
    }
    const out = [], used = new Set();
    for (const o of outfits) {
      if (o.slice(1).some(i => used.has(i.id))) continue;  // vary the items across suggestions
      const full = [...o];
      for (const s of ["layer", "accessory"]) {
        if (!cand[s] || s === mySlot) continue;
        const add = cand[s].find(it => !used.has(it.id) && full.every(x => pairOk(x, it)) &&
          score([...full, it]).score >= score(full).score);
        if (add && (s === "accessory" || anchor.occasion === "formal" || hash(anchor.id + s + seed) % 3 === 0)) full.push(add);
      }
      const sc = score(full);
      out.push({items: full, score: sc.score, max: sc.max, why: sc.why});
      full.slice(1).forEach(i => used.add(i.id));
      if (out.length >= n) break;
    }
    return out.sort((a, b) => b.score - a.score);
  }

  /** Every outfit the catalogue can make for the filters, yielded one at a time (no
   *  cap): anchors spread over category x colour, each completed with completeLook.
   *  f: {style, occasion, band, size, kind} */
  function* outfitStream(catalogue, f = {}, seed = 0) {
    yield* buildOutfits(catalogue, f, Infinity, seed, true);
  }

  /** Up to ``n`` outfits for the filters (n = Infinity: all of them). */
  function buildOutfits(catalogue, f = {}, n = 24, seed = 0, lazy = false) {
    if (lazy) return outfitGen(catalogue, f, n, seed);
    const out = [...outfitGen(catalogue, f, n, seed)];
    return out.sort((a, b) => b.score - a.score);
  }

  function* outfitGen(catalogue, f, n, seed) {
    const kinds = {western: t => t === "western", onepiece: t => t === "onepiece",
                   indian: t => t === "indian", coord: t => t === "coord"};
    const anchors = catalogue.filter(it => {
      const t = templateOf(it);
      if (!t || t === "accessory") return false;
      if (t === "western" && !TOP.has(it.category)) return false;          // anchor on the top
      if (t === "indian" && !(INDIAN_FULL.has(it.category) || INDIAN_TOP.has(it.category))) return false;
      if (f.kind && kinds[f.kind] && !kinds[f.kind](t)) return false;
      if (f.style && it.primary_style !== f.style) return false;
      if (!suitsOccasion(it, f.occasion)) return false;
      if (f.band && it.price_band !== f.band) return false;
      return sizeOk(it, f.size);
    });
    // spread anchors across category x colour, seeded so "more outfits" changes them
    const groups = new Map();
    for (const a of anchors.sort((x, y) => hash(x.id + seed) - hash(y.id + seed))) {
      const k = a.category + "|" + a.color;
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(a);
    }
    // round-robin over the groups so the first outfits are varied; every anchor is tried
    const order = [], lists = [...groups.values()];
    const rounds = Math.max(0, ...lists.map(g => g.length));
    for (let r = 0; r < rounds && order.length < (Number.isFinite(n) ? n * 6 : Infinity); r++)
      for (const g of lists) if (g[r]) order.push(g[r]);
    const pool = f.band ? catalogue.filter(i => !i.price_band || Math.abs(BANDS.indexOf(i.price_band) - BANDS.indexOf(f.band)) <= 1) : catalogue;
    let made = 0;
    const used = new Set(), uses = new Map();
    for (const a of order) {
      if (made >= n) return;
      if (used.has(a.id)) continue;
      const o = completeLook(a, pool, {size: f.size, n: 1, seed, exclude: used});
      if (o.length) {
        made++;
        for (const i of o[0].items) {
          const extra = i.department === "footwear" || i.department === "accessories";
          if (!extra) { used.add(i.id); continue; }
          uses.set(i.id, (uses.get(i.id) || 0) + 1);
          if (uses.get(i.id) >= 3) used.add("^" + i.id);  // footwear / accessory used 3 times
        }
        yield o[0];
      }
    }
  }

  const api = {completeLook, buildOutfits, outfitStream, score, templateOf, pairOk, occasionFamily, sizeOk, suitsOccasion,
               STYLE_PAIRS};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Recommender = api;
})(typeof window !== "undefined" ? window : globalThis);
