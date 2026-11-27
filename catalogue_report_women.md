# Women's catalogue report

## Current catalogue (after the trims)

Updated 2026-11-25 from `data/catalogue_women.db`. **11,814 items**: 7,458 clothes, 1,102 footwear, 3,254 accessories. The build report further down describes the catalogue as first built, before the trims.

### How the catalogue got here

| Step | Items after | Change |
| --- | ---: | --- |
| Built from the scraped feeds (2026-11-21) | 32,882 | 13,614 garments, 1,683 footwear, 17,585 accessories |
| Size trim, clothes (`python -m pipeline.size_trim`) | 31,381 | 1,501 garments removed |
| Size trim, footwear and accessories (`--accessories`) | 23,005 | 8,376 removed |
| Diversity cap (`python -m pipeline.diversity_cap`) | 11,814 | 11,191 removed |

- **Size trim:** items whose detail-panel parameters all match (style, wear type, category, colour, secondary colour, pattern, fit, fabric, sleeve, neckline, occasion) keep one item per size; the rest were deleted permanently.
- **Diversity cap:** at most 10 items per style × category × colour, spread over different varieties (pattern, fit, fabric, sleeve, neckline, sub-type), at most 3 of each. The catalogue from just before this step is in `data/backup_before_diversity/`.

### Items per style

| Style | Clothes | % of clothes | All items | % of all |
| --- | ---: | ---: | ---: | ---: |
| Minimalist | 899 | 12% | 1,429 | 12% |
| Classic | 904 | 12% | 1,534 | 13% |
| Streetwear | 758 | 10% | 1,017 | 8.6% |
| Boho | 861 | 12% | 1,536 | 13% |
| Sporty | 879 | 12% | 919 | 7.8% |
| Glam | 1,192 | 16% | 1,878 | 16% |
| Ethnic fusion | 981 | 13% | 985 | 8.3% |
| Traditional | 621 | 8.3% | 1,431 | 12% |
| Edgy | 363 | 4.9% | 659 | 5.6% |
| Unclassified | 0 | 0% | 426 | 3.6% |

### Departments

| Department | Items | % |
| --- | ---: | ---: |
| topwear | 3,335 | 28% |
| accessories | 3,254 | 28% |
| fullbody | 2,474 | 21% |
| bottomwear | 1,649 | 14% |
| footwear | 1,102 | 9.3% |

### Price bands

| Band | Items | % |
| --- | ---: | ---: |
| cheap | 3,290 | 28% |
| affordable | 4,339 | 37% |
| luxury | 4,185 | 35% |

### Style confidence

| Confidence | Items | % |
| --- | ---: | ---: |
| high | 7,592 | 64% |
| medium | 3,556 | 30% |
| low | 666 | 5.6% |

### Items per site (72 sites)

| Site | Items | % |
| --- | ---: | ---: |
| westside | 1,105 | 9.4% |
| kazo | 799 | 6.8% |
| okhai | 577 | 4.9% |
| littleboxindia | 573 | 4.9% |
| nicobar | 502 | 4.2% |
| berrylush | 498 | 4.2% |
| tjori | 488 | 4.1% |
| sassafras | 315 | 2.7% |
| rareism | 309 | 2.6% |
| suta | 304 | 2.6% |
| bonkerscorner | 302 | 2.6% |
| wforwoman | 280 | 2.4% |
| shopmulmul | 266 | 2.3% |
| street9 | 256 | 2.2% |
| weaverstory | 251 | 2.1% |
| shopforaurelia | 240 | 2.0% |
| torani | 232 | 2.0% |
| aachho | 228 | 1.9% |
| papadontpreach | 216 | 1.8% |
| kicaactive | 198 | 1.7% |
| lakshita | 195 | 1.7% |
| silvertraq | 171 | 1.4% |
| libas | 165 | 1.4% |
| jaipurkurti | 144 | 1.2% |
| cottonworld | 140 | 1.2% |
| chumbak | 134 | 1.1% |
| karagiri | 123 | 1.0% |
| janasya | 120 | 1.0% |
| missprint | 120 | 1.0% |
| aisharao | 117 | 1.0% |
| saundh | 116 | 1.0% |
| saltattire | 111 | 0.9% |
| rustorange | 108 | 0.9% |
| ridhimehra | 104 | 0.9% |
| kharakapas | 102 | 0.9% |
| femmella | 98 | 0.8% |
| tilfi | 90 | 0.8% |
| thelabellife | 89 | 0.8% |
| lavanyathelabel | 87 | 0.7% |
| houseoffett | 85 | 0.7% |
| thekaftancompany | 79 | 0.7% |
| blissclub | 76 | 0.6% |
| chidiyaa | 76 | 0.6% |
| stylestone | 74 | 0.6% |
| ekaya | 70 | 0.6% |
| gulabojaipur | 70 | 0.6% |
| doodlage | 69 | 0.6% |
| thesummerhouse | 68 | 0.6% |
| houseofmasaba | 67 | 0.6% |
| theindianethnicco | 66 | 0.6% |
| seemagujral | 66 | 0.6% |
| ambraee | 59 | 0.5% |
| scakhi | 56 | 0.5% |
| chkokko | 55 | 0.5% |
| labelearthen | 54 | 0.5% |
| bunaai | 49 | 0.4% |
| bohemiandream | 48 | 0.4% |
| duskattire | 47 | 0.4% |
| boldfit | 44 | 0.4% |
| capsul | 42 | 0.4% |
| indoera | 41 | 0.3% |
| houseofchikankari | 34 | 0.3% |
| huemn | 32 | 0.3% |
| vastramay | 32 | 0.3% |
| fuaark | 26 | 0.2% |
| nobero | 24 | 0.2% |
| ituvana | 16 | 0.1% |
| kalakaarihaath | 5 | 0.0% |
| campussutra | 4 | 0.0% |
| veirdo | 3 | 0.0% |
| noughtone | 3 | 0.0% |
| freakins | 1 | 0.0% |

---

## Build report (before the trims)

Generated 2026-11-21 19:01 by `python -m pipeline.run build --gender women`.

**13,614 garments** in the catalogue, chosen from a women's pool of 136,431 items across 77 Indian sites.

### Items per style

| Style | Catalogue | Women's pool | Target 1,450–1,650 | Top keywords that fired |
| --- | ---: | ---: | --- | --- |
| Minimalist | 1,600 | 9,911 | met | solid (1196), brand prior (641), plain (606), clean (436), straight fit (323), relaxed fit (306), minimal (221), everyday (216), co ord (208), essential (202) |
| Classic | 1,600 | 7,423 | met | brand prior (640), shirt (567), formal (449), office (413), workwear (381), office wear (337), work wear (278), striped (249), trousers (229), shirt dress (197) |
| Streetwear | 1,600 | 3,192 | met | oversized (944), brand prior (805), t shirt (729), drop shoulder (472), tee (398), graphic (378), baggy (268), printed (242), hoodies (234), print (224) |
| Boho | 1,600 | 14,790 | met | cotton (966), brand prior (764), floral (654), printed (644), summer (471), maxi (228), hand block (220), vacation (214), resort (213), tiered (206) |
| Sporty | 1,600 | 2,229 | met | brand prior (933), sports (573), yoga (509), gym (472), joggers (426), track pants (423), leggings (348), quick dry (339), sweat wicking (332), athleisure (303) |
| Glam | 1,600 | 18,373 | met | embroidered (730), festive (701), embroidery (531), party (524), wedding (474), embellished (405), brand prior (388), silk (354), sequin (317), festive wear (279) |
| Ethnic fusion | 1,600 | 6,932 | met | brand prior (556), fusion (465), ethnic (320), jacket (293), tunic (229), indo western (178), fusion wear (140), crop top (132), cape (131), pre draped (122) |
| Traditional | 1,600 | 68,466 | met | brand prior (1097), kurta (1093), festive (818), kurta set (586), dupatta (443), suit (427), saree (352), ethnic (336), kurtas (331), chanderi (307) |
| Edgy | 814 | 814 | short by 636 (pool exhausted) | corset (210), leather (177), edgy (165), cutout (144), cut out (131), faux leather (116), mesh (105), zipper (86), cut outs (74), sheer (50) |

Unclassified: 4,301 items (3.2% of the pool; target ≤ 10%). They are left out of the catalogue rather than relabelled.

### Confidence

| Confidence | Items | Share |
| --- | ---: | ---: |
| high | 11,037 | 81% |
| medium | 2,396 | 18% |
| low | 181 | 1% |

### Items per site

Each site is capped at 1,800 items (12% of 15,000).

| Site | Catalogue | Share | Women's pool | Top styles |
| --- | ---: | ---: | ---: | --- |
| bonkerscorner | 990 | 7.3% | 1,584 | Streetwear 758, Sporty 186, Edgy 22 |
| littleboxindia | 742 | 5.5% | 6,554 | Edgy 335, Classic 99, Minimalist 94 |
| westside | 652 | 4.8% | 5,163 | Sporty 173, Classic 99, Streetwear 72 |
| sassafras | 564 | 4.1% | 2,583 | Streetwear 104, Classic 103, Sporty 71 |
| berrylush | 546 | 4.0% | 4,895 | Edgy 150, Minimalist 96, Classic 77 |
| wforwoman | 521 | 3.8% | 9,356 | Minimalist 126, Classic 100, Ethnic fusion 90 |
| kazo | 476 | 3.5% | 3,109 | Minimalist 126, Classic 106, Streetwear 85 |
| rareism | 410 | 3.0% | 4,643 | Minimalist 144, Streetwear 101, Classic 92 |
| suta | 386 | 2.8% | 6,011 | Minimalist 120, Classic 103, Traditional 49 |
| shopforaurelia | 381 | 2.8% | 6,866 | Minimalist 117, Ethnic fusion 59, Classic 55 |
| street9 | 341 | 2.5% | 6,579 | Ethnic fusion 77, Edgy 73, Classic 54 |
| kicaactive | 337 | 2.5% | 392 | Sporty 313, Minimalist 14, Streetwear 7 |
| silvertraq | 333 | 2.4% | 355 | Sporty 322, Classic 5, Streetwear 5 |
| lakshita | 315 | 2.3% | 1,882 | Minimalist 99, Ethnic fusion 73, Glam 46 |
| nicobar | 304 | 2.2% | 1,918 | Minimalist 132, Boho 53, Glam 42 |
| jaipurkurti | 275 | 2.0% | 3,421 | Classic 99, Ethnic fusion 76, Traditional 53 |
| libas | 267 | 2.0% | 23,985 | Classic 68, Ethnic fusion 56, Glam 47 |
| janasya | 228 | 1.7% | 778 | Ethnic fusion 78, Traditional 53, Boho 50 |
| rustorange | 216 | 1.6% | 867 | Ethnic fusion 68, Boho 54, Traditional 52 |
| okhai | 210 | 1.5% | 4,230 | Boho 57, Traditional 46, Glam 41 |
| cottonworld | 194 | 1.4% | 529 | Minimalist 140, Classic 31, Streetwear 20 |
| torani | 191 | 1.4% | 3,107 | Ethnic fusion 58, Boho 45, Glam 40 |
| femmella | 185 | 1.4% | 593 | Classic 85, Minimalist 33, Boho 21 |
| saundh | 179 | 1.3% | 611 | Boho 56, Ethnic fusion 43, Traditional 37 |
| missprint | 179 | 1.3% | 597 | Ethnic fusion 77, Boho 58, Traditional 35 |
| saltattire | 177 | 1.3% | 679 | Classic 116, Glam 38, Boho 13 |
| thelabellife | 175 | 1.3% | 359 | Classic 106, Minimalist 37, Boho 15 |
| houseofmasaba | 172 | 1.3% | 713 | Ethnic fusion 85, Glam 38, Boho 24 |
| shopmulmul | 163 | 1.2% | 3,873 | Boho 48, Ethnic fusion 43, Traditional 35 |
| lavanyathelabel | 161 | 1.2% | 1,000 | Ethnic fusion 65, Glam 45, Traditional 32 |
| tjori | 154 | 1.1% | 766 | Traditional 39, Glam 38, Boho 33 |
| stylestone | 143 | 1.1% | 965 | Traditional 38, Streetwear 24, Classic 22 |
| ambraee | 136 | 1.0% | 868 | Traditional 37, Boho 31, Glam 29 |
| karagiri | 132 | 1.0% | 22,746 | Traditional 53, Glam 44, Ethnic fusion 35 |
| bunaai | 127 | 0.9% | 241 | Traditional 51, Boho 49, Ethnic fusion 14 |
| papadontpreach | 127 | 0.9% | 407 | Ethnic fusion 81, Glam 32, Traditional 9 |
| chidiyaa | 121 | 0.9% | 993 | Boho 51, Traditional 45, Glam 18 |
| blissclub | 120 | 0.9% | 208 | Sporty 89, Classic 18, Streetwear 12 |
| theindianethnicco | 119 | 0.9% | 1,108 | Traditional 53, Boho 45, Minimalist 20 |
| aachho | 118 | 0.9% | 1,248 | Boho 37, Traditional 32, Glam 26 |
| gulabojaipur | 117 | 0.9% | 571 | Boho 38, Glam 37, Traditional 37 |
| houseoffett | 117 | 0.9% | 1,108 | Glam 47, Streetwear 24, Boho 19 |
| ridhimehra | 117 | 0.9% | 1,371 | Ethnic fusion 48, Glam 35, Traditional 26 |
| kharakapas | 108 | 0.8% | 641 | Boho 55, Traditional 22, Classic 16 |
| thekaftancompany | 104 | 0.8% | 658 | Boho 48, Glam 36, Classic 10 |
| indoera | 102 | 0.7% | 6,592 | Traditional 53, Ethnic fusion 28, Glam 15 |
| scakhi | 94 | 0.7% | 636 | Glam 40, Traditional 32, Ethnic fusion 22 |
| weaverstory | 89 | 0.7% | 9,059 | Glam 45, Traditional 33, Ethnic fusion 8 |
| chkokko | 88 | 0.6% | 101 | Sporty 87, Edgy 1 |
| ekaya | 87 | 0.6% | 1,129 | Traditional 35, Glam 30, Boho 6 |
| thesummerhouse | 84 | 0.6% | 456 | Boho 53, Glam 26, Minimalist 4 |
| tilfi | 81 | 0.6% | 2,587 | Glam 42, Traditional 31, Minimalist 4 |
| doodlage | 80 | 0.6% | 244 | Ethnic fusion 34, Streetwear 21, Boho 14 |
| aisharao | 75 | 0.6% | 867 | Glam 47, Ethnic fusion 19, Traditional 7 |
| duskattire | 72 | 0.5% | 145 | Minimalist 31, Boho 20, Glam 12 |
| labelearthen | 71 | 0.5% | 515 | Traditional 46, Boho 11, Glam 9 |
| houseofchikankari | 67 | 0.5% | 884 | Traditional 42, Glam 13, Ethnic fusion 7 |
| bohemiandream | 66 | 0.5% | 175 | Boho 59, Traditional 5, Classic 2 |
| fuaark | 64 | 0.5% | 86 | Sporty 45, Streetwear 18, Edgy 1 |
| boldfit | 62 | 0.5% | 161 | Sporty 55, Streetwear 4, Minimalist 2 |
| vastramay | 61 | 0.4% | 168 | Traditional 43, Ethnic fusion 9, Sporty 5 |
| seemagujral | 51 | 0.4% | 495 | Glam 46, Traditional 4, Ethnic fusion 1 |
| nobero | 46 | 0.3% | 165 | Streetwear 24, Sporty 22 |
| huemn | 39 | 0.3% | 99 | Glam 25, Streetwear 13, Traditional 1 |
| capsul | 37 | 0.3% | 166 | Streetwear 23, Sporty 10, Minimalist 2 |
| ituvana | 36 | 0.3% | 173 | Boho 13, Ethnic fusion 9, Traditional 8 |
| veirdo | 12 | 0.1% | 13 | Streetwear 12 |
| chumbak | 11 | 0.1% | 186 | Boho 8, Ethnic fusion 3 |
| campussutra | 5 | 0.0% | 6 | Streetwear 4, Boho 1 |
| noughtone | 3 | 0.0% | 4 | Streetwear 3 |
| freakins | 1 | 0.0% | 16 | Streetwear 1 |

### Price bands

| Band | Items |
| --- | ---: |
| affordable | 5,058 |
| luxury | 4,609 |
| cheap | 3,947 |

### Departments

| Department | Items |
| --- | ---: |
| topwear | 5,786 |
| fullbody | 4,888 |
| bottomwear | 2,940 |

### What was dropped

| Reason | Products |
| --- | ---: |
| not women's clothing / out of scope | 57,516 |
| same title + colour on one site | 27,330 |
| men | 14,949 |
| unspecified not in a women's collection | 8,382 |
| exact duplicate (title + photo) | 2,554 |
| unisex not in a women's collection | 970 |
| no image | 556 |
| kids (sold only in age sizes) | 351 |
| no price | 67 |

### Sites

| Site | Status | Products in feed | Feed fetched |
| --- | --- | ---: | --- |
| jaywalking | ok | 179 | 2026-11-21T17:36 |
| bluorng | ok | 687 | 2026-11-21T17:36 |
| midnightlaw | ok | 147 | 2026-11-21T17:36 |
| toffle | ok | 312 | 2026-11-21T17:36 |
| noughtone | ok | 51 | 2026-11-21T17:36 |
| bomaachi | ok | 74 | 2026-11-21T17:36 |
| doodlage | ok | 263 | 2026-11-21T17:36 |
| papadontpreach | ok | 855 | 2026-11-21T17:36 |
| duskattire | ok | 257 | 2026-11-21T17:36 |
| femmella | ok | 611 | 2026-11-21T17:36 |
| saltattire | ok | 683 | 2026-11-21T17:36 |
| rareism | ok | 4,836 | 2026-11-21T17:36 |
| kazo | ok | 5,552 | 2026-11-21T17:36 |
| thelabellife | ok | 371 | 2026-11-21T17:36 |
| huemn | ok | 1,064 | 2026-11-21T17:36 |
| labelearthen | ok | 641 | 2026-11-21T17:36 |
| cottonworld | ok | 1,166 | 2026-11-21T17:36 |
| sassafras | ok | 2,752 | 2026-11-21T17:36 |
| thesummerhouse | ok | 504 | 2026-11-21T17:36 |
| kharakapas | ok | 1,458 | 2026-11-21T17:36 |
| nicobar | ok | 16,212 | 2026-11-21T17:37 |
| blissclub | ok | 246 | 2026-11-21T17:36 |
| chkokko | ok | 316 | 2026-11-21T17:36 |
| kicaactive | ok | 490 | 2026-11-21T17:36 |
| silvertraq | ok | 433 | 2026-11-21T17:36 |
| fuaark | ok | 1,083 | 2026-11-21T17:36 |
| boldfit | ok | 611 | 2026-11-21T17:36 |
| nobero | ok | 2,174 | 2026-11-21T17:36 |
| bohemiandream | ok | 179 | 2026-11-21T17:36 |
| saundh | ok | 700 | 2026-11-21T17:36 |
| ituvana | ok | 196 | 2026-11-21T17:36 |
| missprint | ok | 840 | 2026-11-21T17:36 |
| chumbak | ok | 2,134 | 2026-11-21T17:36 |
| thekaftancompany | ok | 1,191 | 2026-11-21T17:36 |
| rustorange | ok | 904 | 2026-11-21T17:36 |
| gulabojaipur | ok | 633 | 2026-11-21T17:36 |
| shopmulmul | ok | 5,416 | 2026-11-21T17:37 |
| okhai | ok | 9,595 | 2026-11-21T17:37 |
| tjori | ok | 2,440 | 2026-11-21T17:37 |
| chidiyaa | ok | 1,094 | 2026-11-21T17:36 |
| kalakaarihaath | ok | 963 | 2026-11-21T17:37 |
| houseofmasaba | ok | 925 | 2026-11-21T17:36 |
| lavanyathelabel | ok | 1,039 | 2026-11-21T17:36 |
| ridhimehra | ok | 1,533 | 2026-11-21T17:37 |
| seemagujral | ok | 619 | 2026-11-21T17:37 |
| aisharao | ok | 1,144 | 2026-11-21T17:37 |
| torani | ok | 5,196 | 2026-11-21T17:37 |
| karagiri | ok | 24,408 | 2026-11-21T17:39 |
| tilfi | ok | 3,517 | 2026-11-21T17:37 |
| ekaya | ok | 1,653 | 2026-11-21T17:37 |
| weaverstory | ok | 13,643 | 2026-11-21T17:38 |
| libas | ok | 24,812 | 2026-11-21T17:55 |
| westside | ok | 15,594 | 2026-11-21T17:38 |
| jaipurkurti | ok | 3,565 | 2026-11-21T17:37 |
| suta | ok | 7,144 | 2026-11-21T17:38 |
| bunaai | ok | 255 | 2026-11-21T17:37 |
| aachho | ok | 2,035 | 2026-11-21T17:38 |
| ambraee | ok | 885 | 2026-11-21T17:37 |
| janasya | ok | 795 | 2026-11-21T17:38 |
| indoera | ok | 6,709 | 2026-11-21T17:38 |
| scakhi | ok | 643 | 2026-11-21T17:38 |
| theindianethnicco | ok | 1,371 | 2026-11-21T17:38 |
| houseofchikankari | ok | 1,077 | 2026-11-21T17:38 |
| lakshita | ok | 1,985 | 2026-11-21T17:38 |
| vastramay | ok | 4,570 | 2026-11-21T17:38 |
| wforwoman | ok | 10,031 | 2026-11-21T17:39 |
| shopforaurelia | ok | 7,612 | 2026-11-21T17:39 |
| bonkerscorner | ok | 3,495 | 2026-11-21T17:38 |
| veirdo | ok | 1,237 | 2026-11-21T17:38 |
| berrylush | ok | 5,403 | 2026-11-21T17:39 |
| littleboxindia | ok | 7,105 | 2026-11-21T17:39 |
| street9 | ok | 7,187 | 2026-11-21T17:39 |
| stylestone | ok | 1,481 | 2026-11-21T17:39 |
| houseoffett | ok | 1,149 | 2026-11-21T17:39 |
| campussutra | ok | 2,875 | 2026-11-21T17:39 |
| capsul | ok | 6,071 | 2026-11-21T17:39 |
| freakins | ok | 30 | 2026-11-21T17:39 |

### Footwear and accessories

**19,268 items**: every women's footwear and accessory product in scope on the same sites (same men's rules; no style balancing). They are stored next to the garments, which are unchanged.

| Department | Category | Items |
| --- | --- | ---: |
| accessories | scarf | 6,354 |
| accessories | jewellery | 6,246 |
| accessories | bag | 2,455 |
| accessories | clutch | 907 |
| accessories | belt | 752 |
| footwear | heels | 486 |
| footwear | sandals | 341 |
| footwear | flats | 336 |
| accessories | hair accessory | 309 |
| footwear | ethnic footwear | 279 |
| footwear | shoes | 241 |
| accessories | cap | 184 |
| accessories | wallet | 109 |
| accessories | watch | 104 |
| accessories | sunglasses | 104 |
| accessories | socks | 61 |

| Style | Items |
| --- | ---: |
| Minimalist | 1,321 |
| Classic | 2,516 |
| Streetwear | 397 |
| Boho | 2,071 |
| Sporty | 49 |
| Glam | 2,596 |
| Ethnic fusion | 4 |
| Traditional | 8,358 |
| Edgy | 715 |
| Unclassified | 1,241 |

| Site | Footwear | Accessories | Total |
| --- | ---: | ---: | ---: |
| weaverstory | 0 | 3,471 | 3,471 |
| kazo | 0 | 2,123 | 2,123 |
| okhai | 1 | 2,089 | 2,090 |
| westside | 661 | 1,080 | 1,741 |
| shopmulmul | 103 | 1,241 | 1,344 |
| tjori | 336 | 880 | 1,216 |
| nicobar | 0 | 1,058 | 1,058 |
| chumbak | 0 | 548 | 548 |
| tilfi | 0 | 543 | 543 |
| wforwoman | 0 | 511 | 511 |
| street9 | 0 | 460 | 460 |
| karagiri | 0 | 411 | 411 |
| aachho | 204 | 194 | 398 |
| shopforaurelia | 4 | 394 | 398 |
| berrylush | 0 | 392 | 392 |
| torani | 0 | 339 | 339 |
| littleboxindia | 214 | 92 | 306 |
| suta | 10 | 278 | 288 |
| libas | 0 | 220 | 220 |
| papadontpreach | 96 | 110 | 206 |
| ekaya | 0 | 127 | 127 |
| theindianethnicco | 0 | 109 | 109 |
| missprint | 0 | 104 | 104 |
| kharakapas | 0 | 98 | 98 |
| aisharao | 0 | 97 | 97 |
| rareism | 17 | 79 | 96 |
| ridhimehra | 0 | 91 | 91 |
| lakshita | 0 | 80 | 80 |
| houseofmasaba | 0 | 60 | 60 |
| gulabojaipur | 0 | 45 | 45 |
| thekaftancompany | 0 | 34 | 34 |
| bonkerscorner | 0 | 28 | 28 |
| seemagujral | 22 | 3 | 25 |
| capsul | 1 | 23 | 24 |
| labelearthen | 0 | 23 | 23 |
| chidiyaa | 0 | 17 | 17 |
| houseofchikankari | 0 | 16 | 16 |
| saundh | 0 | 15 | 15 |
| doodlage | 0 | 14 | 14 |
| boldfit | 12 | 1 | 13 |
| silvertraq | 0 | 12 | 12 |
| thesummerhouse | 0 | 11 | 11 |
| femmella | 0 | 10 | 10 |
| thelabellife | 0 | 10 | 10 |
| sassafras | 0 | 8 | 8 |
| kicaactive | 0 | 8 | 8 |
| ituvana | 2 | 6 | 8 |
| kalakaarihaath | 0 | 6 | 6 |
| ambraee | 0 | 5 | 5 |
| houseoffett | 0 | 3 | 3 |
| saltattire | 0 | 2 | 2 |
| bunaai | 0 | 2 | 2 |
| duskattire | 0 | 1 | 1 |
| blissclub | 0 | 1 | 1 |
| lavanyathelabel | 0 | 1 | 1 |
| stylestone | 0 | 1 | 1 |

Dropped (footwear / accessories):

| Reason | Products |
| --- | ---: |
| unspecified not in a women's collection | 2,250 |
| same title + colour on one site | 684 |
| men | 593 |
| exact duplicate (title + photo) | 356 |
| unisex not in a women's collection | 173 |
| no image | 101 |
| no price | 3 |
