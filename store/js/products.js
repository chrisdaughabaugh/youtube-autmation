/* Product catalog. `art` = CSS background used for the card visual (no external images required).
   In production, replace `art` with real photo URLs and wire this data to your backend / Shopify. */
const PRODUCTS = [
  // ---------- TCG ----------
  {
    id: "tcg-001", name: "Charizard ex — Special Illustration Rare", category: "tcg", tag: "TCG",
    set: "Obsidian Flames", meta: "Pokémon · SIR · Near Mint", price: 189.99, compare: 229.99,
    stock: 3, featured: true, cardName: "Charizard ex", cardSet: "Obsidian Flames",
    art: "radial-gradient(circle at 30% 20%, rgba(255,255,255,.35), transparent 45%), linear-gradient(155deg, #f97316, #ea580c 45%, #7f1d1d)"
  },
  {
    id: "tcg-002", name: "Black Lotus (Reserved List Reprint)", category: "tcg", tag: "TCG",
    set: "30th Anniversary", meta: "Magic · Mythic · Light Play", price: 349.00, compare: null,
    stock: 2, featured: true, cardName: "Black Lotus", cardSet: "MTG · Vintage",
    art: "radial-gradient(circle at 50% 25%, rgba(255,255,255,.25), transparent 45%), linear-gradient(155deg, #1f2937, #0f172a 55%, #000)"
  },
  {
    id: "tcg-003", name: "Monkey D. Luffy — Leader Parallel", category: "tcg", tag: "TCG",
    set: "Romance Dawn", meta: "One Piece · Alt Art · NM", price: 74.50, compare: 89.00,
    stock: 8, featured: true, cardName: "Luffy", cardSet: "Romance Dawn",
    art: "radial-gradient(circle at 30% 20%, rgba(255,255,255,.3), transparent 45%), linear-gradient(155deg, #dc2626, #b91c1c 50%, #450a0a)"
  },
  {
    id: "tcg-004", name: "Elsa, Spirit of Winter — Enchanted", category: "tcg", tag: "TCG",
    set: "The First Chapter", meta: "Lorcana · Enchanted · NM", price: 129.99, compare: null,
    stock: 5, featured: false, cardName: "Elsa", cardSet: "Disney Lorcana",
    art: "radial-gradient(circle at 40% 20%, rgba(255,255,255,.45), transparent 50%), linear-gradient(155deg, #38bdf8, #0ea5e9 50%, #0c4a6e)"
  },
  {
    id: "tcg-005", name: "Umbreon VMAX — Alt Art (Moonbreon)", category: "tcg", tag: "TCG",
    set: "Evolving Skies", meta: "Pokémon · Alt Art · NM", price: 429.00, compare: 499.00,
    stock: 1, featured: true, cardName: "Umbreon VMAX", cardSet: "Evolving Skies",
    art: "radial-gradient(circle at 30% 20%, rgba(250,204,21,.4), transparent 45%), linear-gradient(155deg, #111827, #1e1b4b 55%, #4c1d95)"
  },
  {
    id: "tcg-006", name: "Liliana of the Veil — Borderless", category: "tcg", tag: "TCG",
    set: "Innistrad: Midnight Hunt", meta: "Magic · Rare · NM", price: 41.25, compare: null,
    stock: 12, featured: false, cardName: "Liliana", cardSet: "Midnight Hunt",
    art: "radial-gradient(circle at 40% 20%, rgba(255,255,255,.2), transparent 45%), linear-gradient(155deg, #4b5563, #312e81 55%, #1e1b4b)"
  },
  {
    id: "tcg-007", name: "Pikachu VMAX — Rainbow Rare", category: "tcg", tag: "TCG",
    set: "Vivid Voltage", meta: "Pokémon · Secret Rare · NM", price: 96.00, compare: 115.00,
    stock: 6, featured: false, cardName: "Pikachu VMAX", cardSet: "Vivid Voltage",
    art: "radial-gradient(circle at 35% 20%, rgba(255,255,255,.4), transparent 45%), linear-gradient(155deg, #facc15, #f59e0b 50%, #b45309)"
  },
  {
    id: "tcg-008", name: "Roronoa Zoro — Super Parallel", category: "tcg", tag: "TCG",
    set: "Paramount War", meta: "One Piece · SR · NM", price: 58.00, compare: null,
    stock: 9, featured: false, cardName: "Zoro", cardSet: "Paramount War",
    art: "radial-gradient(circle at 30% 20%, rgba(255,255,255,.3), transparent 45%), linear-gradient(155deg, #22c55e, #16a34a 50%, #14532d)"
  },

  // ---------- Sports ----------
  {
    id: "spt-001", name: "Michael Jordan — Fleer Rookie #57", category: "sports", tag: "Sports",
    set: "1986 Fleer", meta: "NBA · Rookie · Ungraded EX", price: 1250.00, compare: null,
    stock: 1, featured: true, cardName: "M. Jordan", cardSet: "1986 Fleer RC",
    art: "radial-gradient(circle at 30% 20%, rgba(255,255,255,.25), transparent 45%), linear-gradient(155deg, #dc2626, #991b1b 50%, #450a0a)"
  },
  {
    id: "spt-002", name: "Victor Wembanyama — Prizm Silver RC", category: "sports", tag: "Sports",
    set: "2023 Prizm", meta: "NBA · Rookie · Silver", price: 210.00, compare: 260.00,
    stock: 4, featured: true, cardName: "Wembanyama", cardSet: "2023 Prizm",
    art: "radial-gradient(circle at 40% 20%, rgba(255,255,255,.35), transparent 45%), linear-gradient(155deg, #94a3b8, #475569 50%, #1e293b)"
  },
  {
    id: "spt-003", name: "Patrick Mahomes — Optic Rated Rookie", category: "sports", tag: "Sports",
    set: "2017 Optic", meta: "NFL · Rookie · NM", price: 175.50, compare: null,
    stock: 3, featured: false, cardName: "Mahomes", cardSet: "2017 Optic RC",
    art: "radial-gradient(circle at 30% 20%, rgba(255,255,255,.3), transparent 45%), linear-gradient(155deg, #ef4444, #b91c1c 50%, #7f1d1d)"
  },
  {
    id: "spt-004", name: "Shohei Ohtani — Bowman Chrome Auto", category: "sports", tag: "Sports",
    set: "2018 Bowman", meta: "MLB · Auto · NM", price: 540.00, compare: 620.00,
    stock: 2, featured: true, cardName: "Ohtani", cardSet: "2018 Bowman Auto",
    art: "radial-gradient(circle at 40% 20%, rgba(255,255,255,.3), transparent 45%), linear-gradient(155deg, #f87171, #dc2626 45%, #1e3a8a)"
  },
  {
    id: "spt-005", name: "Lionel Messi — Prizm World Cup", category: "sports", tag: "Sports",
    set: "2022 Prizm WC", meta: "Soccer · Base · NM", price: 68.00, compare: null,
    stock: 7, featured: false, cardName: "Messi", cardSet: "2022 World Cup",
    art: "radial-gradient(circle at 35% 20%, rgba(255,255,255,.35), transparent 45%), linear-gradient(155deg, #38bdf8, #2563eb 50%, #1e3a8a)"
  },
  {
    id: "spt-006", name: "LeBron James — Topps Chrome RC", category: "sports", tag: "Sports",
    set: "2003 Topps", meta: "NBA · Rookie · EX-MT", price: 890.00, compare: null,
    stock: 1, featured: false, cardName: "LeBron", cardSet: "2003 Chrome RC",
    art: "radial-gradient(circle at 30% 20%, rgba(250,204,21,.35), transparent 45%), linear-gradient(155deg, #a16207, #713f12 50%, #422006)"
  },

  // ---------- Graded slabs ----------
  {
    id: "grd-001", name: "Charizard Base Set — Holo", category: "graded", tag: "Graded", grade: "PSA 9",
    set: "1999 Base Set", meta: "Pokémon · PSA 9 · Slabbed", price: 2100.00, compare: null,
    stock: 1, featured: true, cardName: "Charizard", cardSet: "1999 Base · PSA 9",
    art: "radial-gradient(circle at 30% 20%, rgba(255,255,255,.35), transparent 45%), linear-gradient(155deg, #f97316, #c2410c 50%, #7c2d12)"
  },
  {
    id: "grd-002", name: "Luka Dončić — Prizm RC", category: "graded", tag: "Graded", grade: "PSA 10",
    set: "2018 Prizm", meta: "NBA · PSA 10 · Gem Mint", price: 640.00, compare: 720.00,
    stock: 2, featured: true, cardName: "Dončić", cardSet: "2018 Prizm · PSA 10",
    art: "radial-gradient(circle at 40% 20%, rgba(255,255,255,.3), transparent 45%), linear-gradient(155deg, #3b82f6, #1d4ed8 50%, #1e3a8a)"
  },
  {
    id: "grd-003", name: "Pikachu Illustrator — Promo", category: "graded", tag: "Graded", grade: "CGC 8",
    set: "1998 Promo", meta: "Pokémon · CGC 8 · Slabbed", price: 4500.00, compare: null,
    stock: 1, featured: false, cardName: "Pikachu", cardSet: "Illustrator · CGC 8",
    art: "radial-gradient(circle at 35% 20%, rgba(255,255,255,.4), transparent 45%), linear-gradient(155deg, #fde047, #eab308 50%, #a16207)"
  },
  {
    id: "grd-004", name: "Tom Brady — Bowman Chrome RC", category: "graded", tag: "Graded", grade: "BGS 9.5",
    set: "2000 Bowman", meta: "NFL · BGS 9.5 · Gem Mint", price: 3200.00, compare: null,
    stock: 1, featured: false, cardName: "Brady", cardSet: "2000 Bowman · BGS 9.5",
    art: "radial-gradient(circle at 30% 20%, rgba(255,255,255,.25), transparent 45%), linear-gradient(155deg, #64748b, #334155 50%, #0f172a)"
  },

  // ---------- Sealed ----------
  {
    id: "seal-001", name: "Pokémon 151 — Booster Bundle (6 packs)", category: "sealed", tag: "Sealed",
    set: "Scarlet & Violet 151", meta: "Pokémon · Factory Sealed", price: 44.99, compare: 54.99,
    stock: 15, featured: true, cardName: "151 Bundle", cardSet: "Sealed Product",
    art: "radial-gradient(circle at 40% 25%, rgba(255,255,255,.3), transparent 50%), linear-gradient(155deg, #f43f5e, #e11d48 45%, #881337)"
  },
  {
    id: "seal-002", name: "MTG Foundations — Play Booster Box", category: "sealed", tag: "Sealed",
    set: "Foundations", meta: "Magic · 36 Packs · Sealed", price: 129.99, compare: null,
    stock: 6, featured: false, cardName: "Booster Box", cardSet: "MTG Foundations",
    art: "radial-gradient(circle at 40% 25%, rgba(255,255,255,.25), transparent 50%), linear-gradient(155deg, #6366f1, #4338ca 50%, #1e1b4b)"
  },
  {
    id: "seal-003", name: "One Piece OP-09 — Booster Box", category: "sealed", tag: "Sealed",
    set: "Emperors in the New World", meta: "One Piece · 24 Packs · Sealed", price: 109.00, compare: 139.00,
    stock: 4, featured: true, cardName: "OP-09 Box", cardSet: "Sealed Product",
    art: "radial-gradient(circle at 40% 25%, rgba(255,255,255,.3), transparent 50%), linear-gradient(155deg, #f59e0b, #d97706 45%, #7c2d12)"
  },
  {
    id: "seal-004", name: "Pokémon Prismatic Evolutions — ETB", category: "sealed", tag: "Sealed",
    set: "Prismatic Evolutions", meta: "Pokémon · Elite Trainer Box", price: 69.99, compare: null,
    stock: 10, featured: false, cardName: "Elite Trainer Box", cardSet: "Sealed Product",
    art: "radial-gradient(circle at 40% 25%, rgba(255,255,255,.35), transparent 50%), linear-gradient(155deg, #a855f7, #7c3aed 50%, #4c1d95)"
  }
];
