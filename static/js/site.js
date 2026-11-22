/* Hourwright front end: consent-gated analytics, affiliate click events,
   listing filters and the compare tool. No dependencies. */
(function () {
  "use strict";
  var root = document.body.dataset.root || "";
  var gaId = document.body.dataset.ga || "";
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage unavailable */ } },
    del: function (k) { try { localStorage.removeItem(k); } catch (e) { /* storage unavailable */ } }
  };
  function $(id) { return document.getElementById(id); }
  function gbp(n) {
    return "£" + Number(n).toLocaleString("en-GB", { minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 });
  }
  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    if (text != null) node.textContent = text;
    return node;
  }

  /* ---- navigation */
  var toggle = document.querySelector(".nav-toggle");
  if (toggle) toggle.addEventListener("click", function () {
    var open = $("site-nav").classList.toggle("open");
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  });

  /* ---- analytics: loaded only after the visitor accepts */
  function loadAnalytics() {
    if (!gaId || window.gtag) return;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", gaId, { anonymize_ip: true });
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(gaId);
    document.head.appendChild(s);
  }
  var banner = $("consent");
  if (gaId && banner) {
    var choice = store.get("hw-consent");
    if (choice === "yes") loadAnalytics();
    else if (choice !== "no") banner.hidden = false;
    $("consent-yes").addEventListener("click", function () { store.set("hw-consent", "yes"); banner.hidden = true; loadAnalytics(); });
    $("consent-no").addEventListener("click", function () { store.set("hw-consent", "no"); banner.hidden = true; });
  }
  var reset = $("consent-reset");
  if (reset) reset.addEventListener("click", function () {
    store.del("hw-consent");
    if (gaId && banner) banner.hidden = false;
    else reset.textContent = "Analytics is not in use on this site";
  });

  /* ---- affiliate click events (sent only when analytics is on) */
  /* Tag the Awin link with the kind of page the click came from (clickref2),
     so Awin reports show which pages lead to clicks and sales. No personal data. */
  function pageType() {
    var seg = location.pathname.split("/").filter(Boolean);
    if (!seg.length || seg[0] === "index.html") return "home";
    if (seg[0] === "watches") {
      if (!seg[1] || seg[1] === "index.html") return "catalogue";
      return /-\d{8,}\.html$/.test(seg[1]) ? "product" : "collections";  /* product slugs end in the feed id */
    }
    return seg[0].replace(/[^a-z-]/g, "").slice(0, 20) || "other";
  }
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest("a[data-aff]");
    if (a && /^https:\/\/www\.awin1\.com\//.test(a.href) && a.href.indexOf("clickref2=") < 0) {
      a.href += "&clickref2=" + pageType();
    }
    if (a && window.gtag) window.gtag("event", "affiliate_click", {
      retailer: a.dataset.aff, product_id: a.dataset.pid || "", page_path: location.pathname
    });
  });

  /* ---- compare selection */
  var MAX = 3;
  function picks() { try { return JSON.parse(store.get("hw-compare") || "[]"); } catch (e) { return []; } }
  function savePicks(list) { store.set("hw-compare", JSON.stringify(list)); renderTray(); }
  function renderTray() {
    var list = picks(), tray = $("tray");
    if (document.getElementById("compare")) return;
    if (!list.length) { if (tray) tray.remove(); return; }
    if (!tray) { tray = el("div", { id: "tray", "class": "tray" }); document.body.appendChild(tray); }
    tray.textContent = "";
    tray.appendChild(el("span", {}, list.length + " of " + MAX + " selected"));
    tray.appendChild(el("a", { href: root + "compare/index.html" }, "Compare now"));
    var clear = el("button", { type: "button", "class": "linkbtn" }, "Clear");
    clear.addEventListener("click", function () { savePicks([]); syncBoxes(); });
    tray.appendChild(clear);
  }
  function syncBoxes() {
    var list = picks();
    document.querySelectorAll(".compare-pick").forEach(function (box) { box.checked = list.indexOf(box.value) > -1; });
  }
  document.addEventListener("change", function (ev) {
    var box = ev.target;
    if (!box.classList || !box.classList.contains("compare-pick")) return;
    var list = picks().filter(function (id) { return id !== box.value; });
    if (box.checked) {
      if (list.length >= MAX) { box.checked = false; return; }
      list.push(box.value);
    }
    savePicks(list);
  });
  syncBoxes();
  renderTray();

  /* ---- listing filters */
  var form = $("filters");
  if (form) {
    var grid = document.querySelector(".grid");
    var cards = Array.prototype.slice.call(grid.querySelectorAll(".card"));
    var original = cards.slice();
    var apply = function () {
      var brand = $("f-brand").value, retailer = $("f-retailer").value;
      var words = $("f-q").value.toLowerCase().split(/\s+/).filter(Boolean);
      var band = $("f-price").value.split("-"), sort = $("f-sort").value;
      var lo = band[0] ? Number(band[0]) : 0, hi = band[1] ? Number(band[1]) : Infinity, shown = 0;
      cards.forEach(function (c) {
        var price = Number(c.dataset.price);
        var ok = (!brand || c.dataset.brand === brand) && (!retailer || c.dataset.retailer === retailer) &&
          price >= lo && price < hi &&
          words.every(function (w) { return (c.dataset.text || "").indexOf(w) > -1; });
        c.hidden = !ok;
        if (ok) shown++;
      });
      var order = sort ? cards.slice().sort(function (a, b) {
        return (Number(a.dataset.price) - Number(b.dataset.price)) * (sort === "asc" ? 1 : -1);
      }) : original;
      order.forEach(function (c) { grid.appendChild(c); });
      $("f-count").textContent = shown + (shown === 1 ? " watch" : " watches");
    };
    form.addEventListener("change", apply);
    $("f-q").addEventListener("input", apply);
    form.addEventListener("submit", function (ev) { ev.preventDefault(); });
    apply();
  }


  /* ---- watch finder: matches only on what the retailer's listing states */
  var finder = $("finder");
  if (finder) {
    var out = $("w-results"), more = $("w-more"), shownMax = 24, rows = [];
    var reading = {};
    try { reading = JSON.parse(finder.dataset.reading || "{}"); } catch (e) { reading = {}; }
    var card = function (p) {
      var a = el("article", { "class": "card" });
      var href = root + "watches/" + p.slug + ".html";
      var thumb = el("a", { "class": "thumb", href: href });
      if (p.image) thumb.appendChild(el("img", { src: p.image, alt: p.brand + " " + p.name, loading: "lazy", width: "320", height: "320", referrerpolicy: "no-referrer" }));
      a.appendChild(thumb);
      a.appendChild(el("p", { "class": "eyebrow" }, p.brand));
      var h = el("h3"); h.appendChild(el("a", { href: href }, p.name)); a.appendChild(h);
      var price = el("p", { "class": "price" }); price.appendChild(el("strong", {}, p.price == null ? "See retailer" : gbp(p.price))); a.appendChild(price);
      var why = [];
      if (p.size) why.push(p.size + "mm case (retailer's listing)");
      if (p.styles.length) why.push(p.styles.join(", ").replace("gmt", "travel/GMT"));
      a.appendChild(el("p", { "class": "meta" }, (why.join(" · ") || "Case size not stated in the listing") + " · " + p.retailer_name));
      var row = el("div", { "class": "row" });
      row.appendChild(el("a", { "class": "btn", href: p.link, rel: "sponsored nofollow noopener", target: "_blank", "data-aff": p.retailer, "data-pid": p.id }, "View at " + p.retailer_name));
      var lab = el("label", { "class": "pick" }); var box = el("input", { type: "checkbox", "class": "compare-pick", value: p.id });
      lab.appendChild(box); lab.appendChild(document.createTextNode(" Compare")); row.appendChild(lab);
      a.appendChild(row);
      return a;
    };
    var run = function (keepMax) {
      if (!keepMax) shownMax = 24;
      var budget = Number($("w-budget").value) || Infinity, style = $("w-style").value, who = $("w-who").value;
      var size = $("w-size").value.split("-"), brand = $("w-brand").value, sort = $("w-sort").value;
      var matches = rows.filter(function (p) {
        if (p.in_stock === false) return false;
        if (p.price != null && p.price > budget) return false;
        if (style && p.styles.indexOf(style) < 0) return false;
        if (who && p.who !== "any" && p.who !== who) return false;
        if (brand && p.b !== brand) return false;
        if (size[0] !== "" && (p.size == null || p.size < Number(size[0]) || p.size >= Number(size[1]))) return false;
        return true;
      }).sort(function (a, b) { return ((a.price || 0) - (b.price || 0)) * (sort === "desc" ? -1 : 1); });
      out.textContent = "";
      matches.slice(0, shownMax).forEach(function (p) { out.appendChild(card(p)); });
      more.hidden = matches.length <= shownMax;
      $("w-count").textContent = matches.length + (matches.length === 1 ? " watch matches" : " watches match");
      var tip = reading[style] || reading[who], box = $("w-reading");
      box.textContent = "";
      if (tip) {
        var p = el("p", { "class": "note" }, "Before you choose: ");
        p.appendChild(el("a", { href: tip.url }, tip.title));
        box.appendChild(p);
      }
      if (!matches.length) out.appendChild(el("p", { "class": "empty" }, "No watches match all of these. Try a higher budget, any size or any brand."));
      syncBoxes();
      if (window.gtag) window.gtag("event", "finder_search", { budget: $("w-budget").value || "any", style: style || "any", size: $("w-size").value || "any", results: matches.length });
    };
    fetch(root + "data/finder.json").then(function (r) { return r.json(); }).then(function (data) {
      rows = data;
      finder.addEventListener("change", function () { run(false); });
      finder.addEventListener("submit", function (ev) { ev.preventDefault(); });
      more.addEventListener("click", function () { shownMax += 24; run(true); });
      run(false);
    }).catch(function () { $("w-count").textContent = "The finder could not load. Browse all watches instead."; });
  }

  /* ---- compare page */
  var host = $("compare");
  if (host && host.dataset.empty !== "feed") {
    var ids = picks();
    if (ids.length) fetch(root + "data/products.json").then(function (r) { return r.json(); }).then(function (all) {
      var chosen = ids.map(function (id) { return all.filter(function (p) { return p.id === id; })[0]; }).filter(Boolean);
      if (!chosen.length) return;
      var fields = [
        ["Watch", function (p, td) {
          if (p.image) td.appendChild(el("img", { src: p.image, alt: "", loading: "lazy", referrerpolicy: "no-referrer" }));
          td.appendChild(el("a", { href: root + "watches/" + p.slug + ".html" }, p.brand + " " + p.name));
        }],
        ["Price", function (p, td) { if (p.price == null) { td.textContent = "See retailer"; return; } td.className = "price"; td.appendChild(el("strong", {}, gbp(p.price))); }],
        ["Retailer", function (p, td) { td.textContent = p.retailer_name; }],
        ["Reference", function (p, td) { td.textContent = p.reference || "Not supplied"; }],
        ["Case size", function (p, td) {
          var m = /(\d{2}(?:\.\d+)?)\s?mm/i.exec(p.name);
          td.textContent = m ? m[1] + "mm (from the retailer's listing)" : "Not stated by the retailer";
        }],
        ["Availability", function (p, td) {
          td.textContent = p.in_stock === true ? "In stock" : p.in_stock === false ? "Out of stock" : "Check with retailer";
        }],
        ["", function (p, td) {
          td.appendChild(el("a", { "class": "btn", href: p.link, rel: "sponsored nofollow noopener", target: "_blank",
            "data-aff": p.retailer, "data-pid": p.id }, "View at " + p.retailer_name));
          var rm = el("button", { type: "button", "class": "linkbtn" }, "Remove");
          rm.addEventListener("click", function () {
            savePicks(picks().filter(function (id) { return id !== p.id; }));
            location.reload();
          });
          td.appendChild(document.createElement("br"));
          td.appendChild(rm);
        }]
      ];
      var table = el("table", { "class": "compare-table" }), body = el("tbody");
      fields.forEach(function (f) {
        var tr = el("tr");
        tr.appendChild(el("th", { scope: "row" }, f[0]));
        chosen.forEach(function (p) { var td = el("td"); f[1](p, td); tr.appendChild(td); });
        body.appendChild(tr);
      });
      table.appendChild(body);
      var wrap = el("div", { "class": "scroll" });
      wrap.appendChild(table);
      host.textContent = "";
      host.appendChild(wrap);
    }).catch(function () { /* leave the empty state in place */ });
  }
})();
