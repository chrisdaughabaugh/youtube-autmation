/* ===== Apex Cards storefront logic ===== */
(function () {
  "use strict";

  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
  const money = (n) => "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const FREE_SHIP = 150;

  let state = { filter: "all", sort: "featured", query: "" };
  let cart = loadCart();
  const wishlist = new Set(loadJSON("apex_wishlist", []));

  /* ---------- Persistence ---------- */
  function loadJSON(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
    catch { return fallback; }
  }
  function loadCart() { return loadJSON("apex_cart", {}); }
  function saveCart() { try { localStorage.setItem("apex_cart", JSON.stringify(cart)); } catch {} }
  function saveWishlist() { try { localStorage.setItem("apex_wishlist", JSON.stringify([...wishlist])); } catch {} }

  const byId = (id) => PRODUCTS.find((p) => p.id === id);

  /* ---------- Product rendering ---------- */
  function visibleProducts() {
    let list = PRODUCTS.filter((p) => state.filter === "all" || p.category === state.filter);
    if (state.query) {
      const q = state.query.toLowerCase();
      list = list.filter((p) =>
        (p.name + " " + p.set + " " + p.meta + " " + p.tag).toLowerCase().includes(q)
      );
    }
    switch (state.sort) {
      case "price-asc": list.sort((a, b) => a.price - b.price); break;
      case "price-desc": list.sort((a, b) => b.price - a.price); break;
      case "name": list.sort((a, b) => a.name.localeCompare(b.name)); break;
      default: list.sort((a, b) => (b.featured === true) - (a.featured === true));
    }
    return list;
  }

  function cardHTML(p) {
    const inCart = cart[p.id];
    const soldOut = p.stock <= 0;
    const gradeBadge = p.grade ? `<span class="badge grade">${p.grade}</span>` : "";
    const catBadge = !p.grade ? `<span class="badge">${p.tag}</span>` : "";
    const compare = p.compare ? `<span class="strike">${money(p.compare)}</span>` : "";
    const lowStock = p.stock > 0 && p.stock <= 3 ? `<span class="stock-low">Only ${p.stock} left</span>` : "";
    const wished = wishlist.has(p.id) ? "active" : "";
    return `
      <article class="card" data-id="${p.id}">
        <div class="card-media">
          <div class="card-art" style="background:${p.art}"></div>
          ${catBadge}${gradeBadge}
          <button class="wish ${wished}" data-wish="${p.id}" aria-label="Add to wishlist" title="Wishlist">
            <svg viewBox="0 0 24 24" width="17" height="17"><path fill="${wished ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2" d="M12 21s-7-4.6-9.3-9C1.2 9 2.5 5.5 6 5.5c2 0 3.2 1.2 4 2.4.8-1.2 2-2.4 4-2.4 3.5 0 4.8 3.5 3.3 6.5C19 16.4 12 21 12 21z"/></svg>
          </button>
          <div class="card-frame">
            <span class="cf-name">${p.cardName}</span>
            <span class="cf-set">${p.cardSet}</span>
          </div>
        </div>
        <div class="card-body">
          <span class="card-cat">${p.set}</span>
          <span class="card-name">${p.name}</span>
          <span class="card-meta">${p.meta}</span>
          <div class="card-foot">
            <div>
              <div class="price">${compare}${money(p.price)}</div>
              ${lowStock}
            </div>
            <button class="add-btn" data-add="${p.id}" ${soldOut ? "disabled" : ""}>
              ${soldOut ? "Sold out" : inCart ? "Added ✓" : "Add"}
            </button>
          </div>
        </div>
      </article>`;
  }

  function renderProducts() {
    const grid = $("#productGrid");
    const list = visibleProducts();
    grid.innerHTML = list.map(cardHTML).join("");
    $("#emptyState").hidden = list.length > 0;
    const n = list.length;
    $("#resultCount").textContent = `${n} card${n === 1 ? "" : "s"} available` +
      (state.filter !== "all" ? ` in ${state.filter}` : "");
    grid.querySelectorAll(".card").forEach((el, i) => { el.style.animationDelay = (i * 0.03) + "s"; });
  }

  /* ---------- Cart ---------- */
  function cartCount() { return Object.values(cart).reduce((s, q) => s + q, 0); }
  function cartSubtotal() {
    return Object.entries(cart).reduce((s, [id, q]) => {
      const p = byId(id); return p ? s + p.price * q : s;
    }, 0);
  }

  function addToCart(id) {
    const p = byId(id);
    if (!p || p.stock <= 0) return;
    const current = cart[id] || 0;
    if (current >= p.stock) { toast(`Only ${p.stock} in stock`); return; }
    cart[id] = current + 1;
    saveCart();
    updateCartUI();
    renderProducts();
    toast(`${p.cardName} added to cart`);
    bumpCartIcon();
  }
  function setQty(id, qty) {
    const p = byId(id);
    if (qty <= 0) { delete cart[id]; }
    else if (p && qty > p.stock) { cart[id] = p.stock; toast(`Only ${p.stock} in stock`); }
    else { cart[id] = qty; }
    saveCart(); updateCartUI(); renderProducts();
  }

  function cartItemHTML(id, qty) {
    const p = byId(id);
    if (!p) return "";
    return `
      <div class="cart-item" data-id="${id}">
        <div class="ci-thumb" style="background:${p.art}"></div>
        <div class="ci-info">
          <div class="ci-name">${p.name}</div>
          <div class="ci-cat">${p.meta}</div>
          <div class="ci-price">${money(p.price * qty)}</div>
          <div class="ci-controls">
            <div class="qty">
              <button data-dec="${id}" aria-label="Decrease">−</button>
              <span>${qty}</span>
              <button data-inc="${id}" aria-label="Increase">+</button>
            </div>
            <button class="ci-remove" data-remove="${id}">Remove</button>
          </div>
        </div>
      </div>`;
  }

  function updateCartUI() {
    const count = cartCount();
    const badge = $("#cartCount");
    badge.textContent = count;
    badge.classList.toggle("show", count > 0);

    const body = $("#cartBody");
    const footer = $("#cartFooter");
    const ids = Object.keys(cart);
    if (ids.length === 0) {
      body.innerHTML = `
        <div class="cart-empty">
          <p>Your cart is empty.</p>
          <p class="muted" style="font-size:.86rem">Add some grails from the vault to get started.</p>
          <button class="btn btn-primary" id="cartShopBtn">Browse the vault</button>
        </div>`;
      footer.classList.add("hidden");
      const b = $("#cartShopBtn");
      if (b) b.addEventListener("click", () => { closeCart(); location.hash = "#shop"; });
      return;
    }
    footer.classList.remove("hidden");
    body.innerHTML = ids.map((id) => cartItemHTML(id, cart[id])).join("");

    const sub = cartSubtotal();
    $("#cartSubtotal").textContent = money(sub);
    const note = $("#shipNote");
    if (sub >= FREE_SHIP) {
      note.textContent = "🎉 You've unlocked free insured shipping!";
      note.classList.remove("progress");
    } else {
      note.textContent = `Add ${money(FREE_SHIP - sub)} more for free insured shipping.`;
      note.classList.add("progress");
    }
  }

  function bumpCartIcon() {
    const btn = $("#cartToggle");
    btn.animate(
      [{ transform: "scale(1)" }, { transform: "scale(1.25)" }, { transform: "scale(1)" }],
      { duration: 300, easing: "cubic-bezier(.22,1,.36,1)" }
    );
  }

  /* ---------- Drawer ---------- */
  const drawer = $("#cartDrawer");
  const overlay = $("#drawerOverlay");
  function openCart() { drawer.classList.add("open"); overlay.classList.add("open"); document.body.style.overflow = "hidden"; }
  function closeCart() { drawer.classList.remove("open"); overlay.classList.remove("open"); document.body.style.overflow = ""; }

  /* ---------- Toast ---------- */
  let toastTimer;
  function toast(msg) {
    const t = $("#toast");
    t.innerHTML = `<span>✓</span> ${msg}`;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 2400);
  }

  /* ---------- Events ---------- */
  function bind() {
    // Filters
    $("#filters").addEventListener("click", (e) => {
      const chip = e.target.closest(".chip");
      if (!chip) return;
      $$(".chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      state.filter = chip.dataset.filter;
      renderProducts();
    });

    // Quick filter links (nav, categories, footer)
    $$("[data-filter-link]").forEach((el) => {
      el.addEventListener("click", () => {
        const f = el.dataset.filterLink;
        state.filter = f;
        $$(".chip").forEach((c) => c.classList.toggle("active", c.dataset.filter === f));
        renderProducts();
        setTimeout(() => $("#shop").scrollIntoView({ behavior: "smooth" }), 60);
        closeMenu();
      });
    });

    // Sort
    $("#sortSelect").addEventListener("change", (e) => { state.sort = e.target.value; renderProducts(); });

    // Product grid (add + wishlist) — event delegation
    $("#productGrid").addEventListener("click", (e) => {
      const add = e.target.closest("[data-add]");
      if (add) { addToCart(add.dataset.add); return; }
      const wish = e.target.closest("[data-wish]");
      if (wish) {
        const id = wish.dataset.wish;
        if (wishlist.has(id)) wishlist.delete(id); else { wishlist.add(id); toast("Saved to wishlist"); }
        saveWishlist(); renderProducts();
      }
    });

    // Cart drawer controls
    $("#cartBody").addEventListener("click", (e) => {
      const inc = e.target.closest("[data-inc]");
      const dec = e.target.closest("[data-dec]");
      const rem = e.target.closest("[data-remove]");
      if (inc) setQty(inc.dataset.inc, (cart[inc.dataset.inc] || 0) + 1);
      else if (dec) setQty(dec.dataset.dec, (cart[dec.dataset.dec] || 0) - 1);
      else if (rem) { setQty(rem.dataset.remove, 0); toast("Removed from cart"); }
    });

    // Cart open/close
    $("#cartToggle").addEventListener("click", openCart);
    $("#cartClose").addEventListener("click", closeCart);
    overlay.addEventListener("click", () => { closeCart(); closeMenu(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") { closeCart(); closeSearch(); } });

    // Checkout (demo)
    $("#checkoutBtn").addEventListener("click", () => {
      const total = cartSubtotal();
      toast(`Demo checkout · ${money(total)}. Connect Stripe/Shopify to go live.`);
    });

    // Search
    $("#searchToggle").addEventListener("click", toggleSearch);
    $("#searchInput").addEventListener("input", (e) => { state.query = e.target.value.trim(); renderProducts(); });

    // Mobile menu
    $("#menuToggle").addEventListener("click", () => $(".nav").classList.toggle("open"));

    // Newsletter + sell (demo)
    $("#newsForm").addEventListener("submit", (e) => { e.preventDefault(); e.target.reset(); toast("You're on the list! Watch your inbox."); });
    $("#sellBtn").addEventListener("click", (e) => { e.preventDefault(); toast("Cash-offer form coming soon — email sell@apexcards.com"); });

    // Header shadow on scroll
    window.addEventListener("scroll", () => {
      $("#siteHeader").style.boxShadow = window.scrollY > 10 ? "0 8px 30px -12px rgba(0,0,0,.6)" : "none";
    });
  }

  function toggleSearch() {
    const bar = $("#searchBar");
    const open = bar.classList.toggle("open");
    if (open) setTimeout(() => $("#searchInput").focus(), 250);
  }
  function closeSearch() { $("#searchBar").classList.remove("open"); }
  function closeMenu() { $(".nav").classList.remove("open"); }

  /* ---------- Init ---------- */
  function init() {
    $("#year").textContent = new Date().getFullYear();
    renderProducts();
    updateCartUI();
    bind();
  }
  document.addEventListener("DOMContentLoaded", init);
})();
