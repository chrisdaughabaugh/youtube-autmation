# Apex Cards — Trading Card Storefront

A professional, responsive storefront for selling **TCG** (Pokémon, Magic, One Piece, Lorcana) and **sports cards** (NBA, NFL, MLB, soccer), plus sealed product and graded slabs.

Pure HTML/CSS/JS — no build step, no dependencies, no external network calls. It runs anywhere you can serve static files.

## Features

- **Storefront**: hero, category tiles, filterable/sortable product grid, value props, about/sell section, newsletter, footer.
- **Filtering & search**: filter by TCG / Sports / Sealed / Graded, sort by price or name, live search.
- **Cart**: slide-out drawer, quantity controls, stock limits, subtotal, free-shipping progress, persisted to `localStorage`.
- **Wishlist**: heart any card, saved to `localStorage`.
- **Responsive**: 4-col desktop down to single-column mobile, with a mobile nav menu.
- **No image dependencies**: card art is generated with CSS gradients, so nothing breaks in a restricted network.

## Run it

```bash
cd store
python3 -m http.server 8000
# open http://localhost:8000
```

Or just open `store/index.html` directly in a browser.

## Going live (real sales)

The catalog lives in `js/products.js`. To sell for real:

1. **Products** — replace the `art` gradient on each item with real photo URLs, and connect the array to your backend or a headless CMS.
2. **Payments** — wire the **Checkout** button (`#checkoutBtn` in `js/app.js`) to **Stripe Checkout** or **Shopify**. The cart shape (`{ productId: qty }`) maps cleanly to line items.
3. **Inventory** — `stock` per product already drives "Only N left" and sold-out states; sync it from your source of truth.

Shopify note: this repo's environment has a Shopify MCP integration available — the same catalog can be pushed to a real Shopify store if you want hosted checkout, tax, and shipping handled for you.

## Structure

```
store/
├── index.html        # markup
├── css/styles.css    # design system + responsive layout
└── js/
    ├── products.js   # catalog data (edit this to change inventory)
    └── app.js        # rendering, filtering, cart, wishlist
```
