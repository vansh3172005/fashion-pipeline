# Men's catalogue report

## Current catalogue (after the trims)

Updated 2026-11-25 from `data/catalogue.db`. **6,525 items**: 5,121 clothes, 446 footwear, 958 accessories. The build report further down describes the catalogue as first built, before the trims.

### How the catalogue got here

| Step | Items after | Change |
| --- | ---: | --- |
| Built from the scraped feeds (2026-11-20) | 17,445 | 13,957 garments, 1,426 footwear, 2,062 accessories |
| Size trim, clothes (`python -m pipeline.size_trim`) | 14,042 | 3,403 garments removed |
| Size trim, footwear and accessories (`--accessories`) | 12,463 | 1,579 removed |
| Diversity cap (`python -m pipeline.diversity_cap`) | 6,525 | 5,938 removed |

- **Size trim:** items whose detail-panel parameters all match (style, wear type, category, colour, secondary colour, pattern, fit, fabric, sleeve, neckline, occasion) keep one item per size; the rest were deleted permanently.
- **Diversity cap:** at most 10 items per style × category × colour, spread over different varieties (pattern, fit, fabric, sleeve, neckline, sub-type), at most 3 of each. The catalogue from just before this step is in `data/backup_before_diversity/`.

### Items per style

| Style | Clothes | % of clothes | All items | % of all |
| --- | ---: | ---: | ---: | ---: |
| Minimalist | 854 | 17% | 1,079 | 17% |
| Classic | 682 | 13% | 1,143 | 18% |
| Streetwear | 910 | 18% | 1,325 | 20% |
| Boho | 407 | 7.9% | 437 | 6.7% |
| Sporty | 557 | 11% | 621 | 9.5% |
| Glam | 654 | 13% | 749 | 11% |
| Ethnic fusion | 510 | 10.0% | 510 | 7.8% |
| Traditional | 547 | 11% | 613 | 9.4% |
| Unclassified | 0 | 0% | 48 | 0.7% |

### Departments

| Department | Items | % |
| --- | ---: | ---: |
| topwear | 3,351 | 51% |
| bottomwear | 1,037 | 16% |
| accessories | 958 | 15% |
| fullbody | 733 | 11% |
| footwear | 446 | 6.8% |

### Price bands

| Band | Items | % |
| --- | ---: | ---: |
| cheap | 1,631 | 25% |
| affordable | 2,736 | 42% |
| luxury | 2,158 | 33% |

### Style confidence

| Confidence | Items | % |
| --- | ---: | ---: |
| high | 4,738 | 73% |
| medium | 1,529 | 23% |
| low | 258 | 4.0% |

### Items per site (38 sites)

| Site | Items | % |
| --- | ---: | ---: |
| snitch | 618 | 9.5% |
| houseofrare | 559 | 8.6% |
| kisah | 427 | 6.5% |
| blackberrys | 371 | 5.7% |
| vastramay | 364 | 5.6% |
| wrogn | 302 | 4.6% |
| styleunion | 295 | 4.5% |
| campussutra | 283 | 4.3% |
| thebearhouse | 274 | 4.2% |
| jompers | 250 | 3.8% |
| capsul | 241 | 3.7% |
| powerlook | 216 | 3.3% |
| nobero | 212 | 3.2% |
| bananaclub | 209 | 3.2% |
| jadeblue | 209 | 3.2% |
| bonkerscorner | 161 | 2.5% |
| nicobar | 158 | 2.4% |
| sojanya | 150 | 2.3% |
| sanwara | 136 | 2.1% |
| canvasandweaves | 132 | 2.0% |
| dennislingo | 132 | 2.0% |
| fuaark | 106 | 1.6% |
| urbanmonkey | 93 | 1.4% |
| andamen | 86 | 1.3% |
| fugazee | 82 | 1.3% |
| chkokko | 74 | 1.1% |
| boldfit | 60 | 0.9% |
| mydesignation | 53 | 0.8% |
| saphed | 52 | 0.8% |
| underratedclub | 35 | 0.5% |
| jodi | 33 | 0.5% |
| ethnicplus | 30 | 0.5% |
| okhai | 26 | 0.4% |
| almostgods | 25 | 0.4% |
| manan | 22 | 0.3% |
| houseofmasaba | 18 | 0.3% |
| houseofmen | 17 | 0.3% |
| offduty | 14 | 0.2% |

---

## Build report (before the trims)

Generated 2026-11-21 15:04 by `python -m pipeline.run build`.

**13,957 garments** in the catalogue, chosen from a men's pool of 72,330 items across 41 Indian sites.

### Items per style

| Style | Catalogue | Men's pool | Target 1,600–1,900 | Top keywords that fired |
| --- | ---: | ---: | --- | --- |
| Minimalist | 1,875 | 12,705 | met | solid (1262), brand prior (1027), clean (784), plain (721), relaxed fit (513), essential (410), minimal (254), everyday (224), minimalist (182), straight fit (179) |
| Classic | 1,875 | 20,965 | met | brand prior (1821), regular fit (697), polo (520), striped (509), slim fit (476), formal (453), trousers (392), office (352), check (310), office wear (271) |
| Streetwear | 1,875 | 14,076 | met | brand prior (1547), oversized (1123), graphic (660), printed (568), street (473), streetwear (442), print (400), street wear (386), baggy (322), boxy (252) |
| Boho | 1,512 | 1,512 | short by 88 (pool exhausted) | printed (670), floral (669), brand prior (275), linen (193), crochet (192), relaxed (160), paisley (142), tie dye (141), resort (97), shacket (77) |
| Sporty | 1,761 | 1,761 | met | joggers (734), brand prior (596), jogger (387), gym (274), track pants (273), running (256), shorts (227), trackpants (216), performance (198), athleisure (136) |
| Glam | 1,875 | 3,973 | met | embroidered (1129), silk (1053), wedding (1052), brand prior (906), embroidery (809), sangeet (796), festive (381), sequin (297), jacquard (259), reception (230) |
| Ethnic fusion | 1,309 | 1,309 | short by 291 (pool exhausted) | brand prior (988), nehru jacket (497), indo western (366), jacket set (309), indo western set (195), jodhpuri (194), kurta jacket (126), fusion (80), short kurta (34), bandhgala (24) |
| Traditional | 1,875 | 9,893 | met | kurta (1729), brand prior (1594), kurta set (998), ethnic (878), pyjama (830), kurta pyjama (740), festive (664), ethnic wear (482), churidar (432), kurtas (394) |

Unclassified: 6,136 items (8.5% of the pool; target ≤ 10%). They are left out of the catalogue rather than relabelled.

### Confidence

| Confidence | Items | Share |
| --- | ---: | ---: |
| high | 10,439 | 75% |
| medium | 3,102 | 22% |
| low | 416 | 3% |

### Items per site

Each site is capped at 1,800 items (12% of 15,000).

| Site | Catalogue | Share | Men's pool | Top styles |
| --- | ---: | ---: | ---: | --- |
| snitch | 1,524 | 10.9% | 23,306 | Boho 642, Sporty 221, Minimalist 179 |
| jompers | 977 | 7.0% | 4,712 | Ethnic fusion 380, Glam 297, Traditional 279 |
| vastramay | 853 | 6.1% | 3,016 | Glam 378, Ethnic fusion 237, Traditional 233 |
| kisah | 849 | 6.1% | 2,787 | Glam 349, Ethnic fusion 295, Traditional 201 |
| sojanya | 705 | 5.1% | 1,779 | Glam 329, Traditional 300, Ethnic fusion 76 |
| houseofrare | 685 | 4.9% | 6,090 | Minimalist 203, Classic 155, Streetwear 126 |
| jadeblue | 663 | 4.8% | 8,714 | Traditional 230, Classic 156, Sporty 125 |
| wrogn | 630 | 4.5% | 5,182 | Sporty 170, Minimalist 157, Streetwear 152 |
| campussutra | 617 | 4.4% | 2,872 | Classic 162, Minimalist 136, Boho 131 |
| styleunion | 591 | 4.2% | 2,036 | Minimalist 165, Traditional 144, Classic 119 |
| thebearhouse | 477 | 3.4% | 2,517 | Minimalist 196, Classic 169, Streetwear 95 |
| powerlook | 447 | 3.2% | 2,071 | Streetwear 140, Classic 133, Sporty 65 |
| bananaclub | 403 | 2.9% | 2,129 | Classic 160, Boho 84, Streetwear 67 |
| nobero | 398 | 2.9% | 1,625 | Sporty 154, Streetwear 151, Minimalist 50 |
| sanwara | 381 | 2.7% | 1,248 | Traditional 291, Ethnic fusion 62, Glam 28 |
| andamen | 336 | 2.4% | 3,403 | Classic 171, Minimalist 66, Sporty 52 |
| dennislingo | 332 | 2.4% | 1,183 | Minimalist 166, Classic 134, Sporty 25 |
| blackberrys | 329 | 2.4% | 4,766 | Classic 155, Minimalist 105, Boho 29 |
| nicobar | 326 | 2.3% | 817 | Minimalist 168, Traditional 63, Boho 52 |
| bonkerscorner | 325 | 2.3% | 1,507 | Sporty 174, Streetwear 124, Minimalist 21 |
| fuaark | 276 | 2.0% | 838 | Sporty 276 |
| canvasandweaves | 216 | 1.5% | 621 | Boho 108, Minimalist 35, Ethnic fusion 26 |
| underratedclub | 195 | 1.4% | 510 | Streetwear 175, Minimalist 7, Sporty 7 |
| urbanmonkey | 185 | 1.3% | 390 | Streetwear 154, Sporty 21, Boho 6 |
| ethnicplus | 183 | 1.3% | 194 | Glam 131, Ethnic fusion 52 |
| capsul | 173 | 1.2% | 1,097 | Streetwear 97, Sporty 64, Boho 12 |
| fugazee | 138 | 1.0% | 435 | Streetwear 108, Sporty 16, Boho 10 |
| mydesignation | 133 | 1.0% | 476 | Streetwear 81, Boho 25, Sporty 20 |
| chkokko | 115 | 0.8% | 146 | Sporty 115 |
| saphed | 104 | 0.7% | 216 | Traditional 51, Minimalist 26, Boho 11 |
| manan | 91 | 0.7% | 147 | Boho 51, Traditional 40 |
| jodi | 53 | 0.4% | 70 | Boho 42, Ethnic fusion 11 |
| boldfit | 51 | 0.4% | 116 | Sporty 51 |
| offduty | 48 | 0.3% | 149 | Streetwear 28, Sporty 14, Boho 3 |
| houseofmen | 44 | 0.3% | 48 | Streetwear 42, Minimalist 2 |
| houseofmasaba | 38 | 0.3% | 117 | Glam 20, Traditional 12, Boho 5 |
| okhai | 37 | 0.3% | 56 | Boho 35, Ethnic fusion 2 |
| almostgods | 29 | 0.2% | 121 | Streetwear 18, Boho 10, Sporty 1 |

### Price bands

| Band | Items |
| --- | ---: |
| affordable | 6,876 |
| luxury | 4,209 |
| cheap | 2,872 |

### Departments

| Department | Items |
| --- | ---: |
| topwear | 8,963 |
| bottomwear | 2,967 |
| fullbody | 2,027 |

### What was dropped

| Reason | Products |
| --- | ---: |
| not apparel / out of scope | 43,569 |
| women | 40,433 |
| same title + colour on one site | 10,629 |
| unspecified not in a men's collection | 8,075 |
| exact duplicate (title + photo) | 4,556 |
| unisex not in a men's collection | 1,556 |
| kids (sold only in age sizes) | 200 |
| no image | 45 |
| no price | 1 |

### Sites

| Site | Status | Products in feed | Feed fetched |
| --- | --- | ---: | --- |
| snitch | ok | 24,155 | 2026-11-20T20:39 |
| andamen | ok | 3,852 | 2026-11-20T20:37 |
| bananaclub | ok | 2,178 | 2026-11-20T20:39 |
| blackberrys | ok | 5,412 | 2026-11-20T20:39 |
| campussutra | ok | 2,875 | 2026-11-20T20:38 |
| jadeblue | ok | 8,808 | 2026-11-20T20:39 |
| jompers | ok | 5,064 | 2026-11-20T20:38 |
| kisah | ok | 3,115 | 2026-11-20T20:38 |
| powerlook | ok | 2,127 | 2026-11-20T20:37 |
| sojanya | ok | 1,784 | 2026-11-20T20:37 |
| thebearhouse | ok | 2,853 | 2026-11-20T20:38 |
| wrogn | ok | 5,673 | 2026-11-20T20:39 |
| houseofmen | ok | 50 | 2026-11-20T20:37 |
| mydesignation | ok | 546 | 2026-11-20T20:38 |
| sanwara | ok | 1,498 | 2026-11-20T20:39 |
| almostgods | ok | 189 | 2026-11-20T20:37 |
| capsul | ok | 6,071 | 2026-11-20T20:37 |
| fugazee | ok | 474 | 2026-11-20T20:37 |
| urbanmonkey | ok | 1,398 | 2026-11-20T20:37 |
| offduty | ok | 591 | 2026-11-20T20:37 |
| canvasandweaves | ok | 14,581 | 2026-11-20T20:39 |
| manan | ok | 1,258 | 2026-11-20T20:37 |
| houseofmasaba | ok | 925 | 2026-11-20T20:37 |
| fuaark | ok | 1,088 | 2026-11-20T20:38 |
| saphed | ok | 429 | 2026-11-20T20:37 |
| vastramay | ok | 4,570 | 2026-11-20T20:38 |
| nicobar | ok | 16,213 | 2026-11-20T20:39 |
| nobero | ok | 2,174 | 2026-11-20T20:38 |
| dennislingo | ok | 1,942 | 2026-11-20T20:38 |
| underratedclub | ok | 887 | 2026-11-20T20:38 |
| boldfit | ok | 611 | 2026-11-20T20:38 |
| jodi | ok | 886 | 2026-11-20T20:38 |
| houseofrare | ok | 14,798 | 2026-11-20T20:39 |
| styleunion | ok | 14,524 | 2026-11-20T20:40 |
| chkokko | ok | 309 | 2026-11-20T20:37 |
| bonkerscorner | ok | 3,495 | 2026-11-20T20:37 |
| ethnicplus | ok | 13,365 | 2026-11-20T20:40 |
| okhai | ok | 9,565 | 2026-11-20T20:39 |
| bluorng | ok | 687 | 2026-11-20T20:37 |
| six5six | ok | 195 | 2026-11-20T20:37 |
| jaywalking | ok | 179 | 2026-11-20T20:37 |

### Footwear and accessories

**3,488 items**: every men's footwear and accessory product in scope on the same sites (same men's rules; no style balancing). They are stored next to the garments, which are unchanged.

| Department | Category | Items |
| --- | --- | ---: |
| footwear | shoes | 1,189 |
| accessories | cap | 372 |
| accessories | socks | 356 |
| accessories | belt | 292 |
| accessories | bag | 273 |
| accessories | sunglasses | 237 |
| footwear | sandals | 235 |
| accessories | tie | 219 |
| accessories | jewellery | 153 |
| accessories | scarf | 109 |
| accessories | wallet | 51 |
| footwear | ethnic footwear | 2 |

| Style | Items |
| --- | ---: |
| Minimalist | 460 |
| Classic | 1,409 |
| Streetwear | 1,138 |
| Boho | 34 |
| Sporty | 82 |
| Glam | 209 |
| Traditional | 84 |
| Unclassified | 72 |

| Site | Footwear | Accessories | Total |
| --- | ---: | ---: | ---: |
| houseofrare | 668 | 111 | 779 |
| blackberrys | 135 | 503 | 638 |
| snitch | 137 | 428 | 565 |
| wrogn | 285 | 66 | 351 |
| thebearhouse | 65 | 236 | 301 |
| capsul | 7 | 288 | 295 |
| vastramay | 20 | 60 | 80 |
| boldfit | 68 | 2 | 70 |
| fuaark | 0 | 64 | 64 |
| sanwara | 1 | 49 | 50 |
| powerlook | 0 | 46 | 46 |
| styleunion | 1 | 42 | 43 |
| bananaclub | 37 | 4 | 41 |
| nicobar | 0 | 41 | 41 |
| bonkerscorner | 0 | 29 | 29 |
| okhai | 0 | 28 | 28 |
| mydesignation | 0 | 21 | 21 |
| kisah | 0 | 13 | 13 |
| urbanmonkey | 0 | 13 | 13 |
| dennislingo | 0 | 10 | 10 |
| almostgods | 1 | 7 | 8 |
| andamen | 1 | 0 | 1 |
| jodi | 0 | 1 | 1 |

Dropped (footwear / accessories):

| Reason | Products |
| --- | ---: |
| women | 6,281 |
| unspecified not in a men's collection | 3,052 |
| garment set sold with a dupatta / safa (clothing, not an accessory) | 1,383 |
| unisex not in a men's collection | 707 |
| exact duplicate (title + photo) | 181 |
| same title + colour on one site | 94 |
