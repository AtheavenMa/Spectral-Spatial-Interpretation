"use strict";

/* Visual Atlas: real, unmodified rendered SSI examples.
 * All 57 gallery PNGs are indexed from the project examples/ directory.
 * Only the dedicated HLS tab runs SSI in this static browser. A gallery PNG
 * never substitutes for a new model inference result.
 */
(() => {
  const $ = (id) => document.getElementById(id);
  let catalog = null;
  let activeGroup = null;
  let activeImage = null;

  function setTab(atlas) {
    $("computeView").hidden = atlas;
    $("atlasView").hidden = !atlas;
    $("computeTab").classList.toggle("selected", !atlas);
    $("atlasTab").classList.toggle("selected", atlas);
    $("computeTab").setAttribute("aria-selected", String(!atlas));
    $("atlasTab").setAttribute("aria-selected", String(atlas));
    if (atlas) loadCatalog();
  }

  async function loadCatalog() {
    if (catalog) {
      renderFilters();
      renderGroup();
      return;
    }
    $("atlasGallery").textContent = "Loading examples…";
    try {
      const res = await fetch("./atlas-catalog.json");
      if (!res.ok) throw new Error("Atlas catalog unavailable");
      catalog = await res.json();
      const all = catalog.groups.reduce((n, group) => n + group.files.length, 0);
      if (all !== 57 || catalog.count !== all) throw new Error("Incomplete Visual Atlas");
      const requested = new URLSearchParams(location.search).get("dataset");
      activeGroup = catalog.groups.some(group => group.id === requested) ?
        requested : catalog.groups[0].id;
      renderFilters();
      renderGroup();
    } catch (error) {
      $("atlasGallery").textContent = "Could not load the Atlas. " + error.message;
    }
  }

  function renderFilters() {
    const target = $("datasetFilters");
    target.replaceChildren();
    if (!catalog) return;
    for (const group of catalog.groups) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "dataset-filter" + (group.id === activeGroup ? " selected" : "");
      btn.textContent = group.label + " · " + group.files.length;
      btn.setAttribute("aria-pressed", String(group.id === activeGroup));
      btn.addEventListener("click", () => {
        activeGroup = group.id;
        renderFilters();
        renderGroup();
        const params = new URLSearchParams(location.search);
        params.set("view", "atlas");
        params.set("dataset", group.id);
        history.replaceState(null, "", location.pathname + "?" + params);
      });
      target.append(btn);
    }
  }

  function renderGroup() {
    if (!catalog) return;
    const group = catalog.groups.find(g => g.id === activeGroup);
    const gallery = $("atlasGallery");
    gallery.replaceChildren();
    if (!group) return;
    group.files.forEach((name, index) => {
      const url = group.raw_prefix + name;
      const card = document.createElement("button");
      card.className = "atlas-tile";
      card.type = "button";
      card.setAttribute("aria-label", "Open " + group.label + " " + name);
      const image = document.createElement("img");
      image.src = url;
      image.alt = group.label + " SSI figure " + name.replace(/\.png$/, "");
      image.loading = index < 3 ? "eager" : "lazy";
      image.decoding = index < 3 ? "sync" : "async";
      const line = document.createElement("span");
      line.className = "atlas-tile-info";
      const text = document.createElement("span");
      text.textContent = name.replace(/\.png$/, "").replace("sample_", "Example ");
      const link = document.createElement("span");
      link.textContent = "Expand ↗";
      line.append(text, link);
      card.append(image, line);
      card.addEventListener("click", () => openImage(group, name, index));
      gallery.append(card);
    });
  }

  function openImage(group, name, index) {
    activeImage = group.raw_prefix + name;
    $("atlasDialogImage").src = activeImage;
    $("atlasDialogTitle").textContent = group.label + " · " + name.replace(".png", "");
    $("atlasFullLink").href = activeImage;
    $("atlasNumber").textContent = (index + 1) + " / " + group.files.length;
    $("atlasDialog").showModal();
  }

  function closeDialog() {
    $("atlasDialog").close();
    $("atlasDialogImage").removeAttribute("src");
  }

  $("computeTab").addEventListener("click", () => {
    setTab(false);
    window.dispatchEvent(new Event("ssi-open-compute"));
    const params = new URLSearchParams(location.search);
    params.delete("view");
    params.delete("dataset");
    history.replaceState(null, "", location.pathname + "?" + params);
  });
  $("atlasTab").addEventListener("click", () => {
    setTab(true);
    const params = new URLSearchParams(location.search);
    params.set("view", "atlas");
    history.replaceState(null, "", location.pathname + "?" + params);
  });
  $("atlasClose").addEventListener("click", closeDialog);
  $("atlasDialog").addEventListener("click", (event) => {
    if (event.target === $("atlasDialog")) closeDialog();
  });
  if (new URLSearchParams(location.search).get("view") === "atlas") setTab(true);
})();
