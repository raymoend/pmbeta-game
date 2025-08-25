(function () {
  const API_BASE = "/api";
  const SRC_ID = "flags_source";
  const LAYER_ID = "flags_layer";
  const POLL_RADIUS_M = 800;

  function getCSRF() {
    const name = "csrftoken=";
    const parts = document.cookie.split(";").map(s => s.trim());
    for (const p of parts) if (p.startsWith(name)) return decodeURIComponent(p.slice(name.length));
    return null;
  }

  async function apiGet(url) {
    const r = await fetch(url, { credentials: "include" });
    return r.json();
  }
  async function apiPost(url, body) {
    const r = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/x-www-form-urlencoded", "X-CSRFToken": getCSRF() || "" },
      body: new URLSearchParams(body || {}).toString(),
    });
    return r.json();
  }

  function toFeature(f) {
    return {
      type: "Feature",
      geometry: { type: "Point", coordinates: [f.lon, f.lat] },
      properties: {
        id: f.id,
        owner_id: f.owner_id,
        level: f.level,
        status: f.status,
        name: f.name || "",
        hp: f.hp_current,
        hp_max: f.hp_max,
        uncollected_balance: f.uncollected_balance || 0,
        color: f.color || null,
      },
    };
  }

  async function loadNear(map, me) {
    const c = map.getCenter();
    const url = `${API_BASE}/flags/near/?lat=${c.lat}&lon=${c.lng}&radius_m=${POLL_RADIUS_M}`;
    const data = await apiGet(url);
    const features = (data.flags || []).map(toFeature);
    const fc = { type: "FeatureCollection", features };
    if (map.getSource(SRC_ID)) {
      map.getSource(SRC_ID).setData(fc);
    } else {
      map.addSource(SRC_ID, { type: "geojson", data: fc });
      map.addLayer({
        id: LAYER_ID,
        type: "circle",
        source: SRC_ID,
        paint: {
          "circle-color": [
            "coalesce",
            ["get", "color"],
            ["case",
              ["==", ["get", "owner_id"], me], "#2ecc71",
              ["==", ["get", "status"], "capturable"], "#f1c40f",
              ["==", ["get", "status"], "under_attack"], "#e67e22",
              "#e74c3c"
            ]
          ],
          "circle-radius": ["+", ["*", ["get", "level"], 4], 8],
          "circle-opacity": 0.8,
          "circle-stroke-color": "#222222",
          "circle-stroke-width": 1.5,
        },
      });
    }
  }

  function bindInteractions(map, socket, me) {
    const panel = document.getElementById("flag-panel");
    const btnPlace = document.getElementById("btn-place-flag");
    const btnAttack = document.getElementById("btn-attack-flag");
    const btnCapture = document.getElementById("btn-capture-flag");
    const btnCollect = document.getElementById("btn-collect-flag");
    let placing = false;
    let selectedId = null;

    if (btnPlace) {
      btnPlace.addEventListener("click", () => {
        placing = !placing;
        btnPlace.textContent = placing ? "Click map to place..." : "Place Flag";
      });
    }

    map.on("click", async (e) => {
      if (!placing) return;
      placing = false;
      if (btnPlace) btnPlace.textContent = "Place Flag";
      const lat = e.lngLat.lat;
      const lon = e.lngLat.lng;
      const resp = await apiPost(`${API_BASE}/flags/place/`, { lat, lon });
      if (resp.ok) {
        await loadNear(map, me);
      } else {
        alert("Could not place flag");
      }
    });

    if (map.on && map.getLayer && panel) {
      map.on("click", LAYER_ID, (e) => {
        const f = e.features[0];
        selectedId = f.properties.id;
        panel.querySelector(".flag-id").textContent = selectedId;
        panel.querySelector(".flag-owner").textContent = f.properties.owner_id;
        panel.querySelector(".flag-level").textContent = f.properties.level;
        panel.querySelector(".flag-status").textContent = f.properties.status;
        panel.style.display = "block";
      });
    }

    if (btnAttack) btnAttack.addEventListener("click", async () => {
      if (!selectedId) return;
      const c = map.getCenter();
      const resp = await apiPost(`${API_BASE}/flags/${selectedId}/attack/`, { lat: c.lat, lon: c.lng });
      if (!resp.ok) alert("Attack failed");
    });

    if (btnCapture) btnCapture.addEventListener("click", async () => {
      if (!selectedId) return;
      const resp = await apiPost(`${API_BASE}/flags/${selectedId}/capture/`, {});
      if (!resp.ok) alert("Capture failed");
    });

    if (btnCollect) btnCollect.addEventListener("click", async () => {
      if (!selectedId) return;
      const resp = await apiPost(`${API_BASE}/flags/${selectedId}/collect/`, {});
      if (!resp.ok) alert("Collect failed");
    });

    function handleFlagEvent(msg) {
      if (msg.type !== "flag_event") return;
      const f = toFeature(msg.flag);
      const src = map.getSource(SRC_ID);
      if (!src) return;
      const data = src._data || src._options?.data || { type: "FeatureCollection", features: [] };
      const idx = data.features.findIndex(x => x.properties.id === f.properties.id);
      if (idx >= 0) data.features[idx] = f; else data.features.push(f);
      src.setData(data);
    }

    if (socket && socket.addEventListener) {
      socket.addEventListener("message", (ev) => {
        try { handleFlagEvent(JSON.parse(ev.data)); } catch (e) {}
      });
    } else if (socket && socket.onmessage) {
      const old = socket.onmessage;
      socket.onmessage = function (ev) {
        try { handleFlagEvent(JSON.parse(ev.data)); } catch (e) {}
        if (old) old(ev);
      };
    }

    map.on("moveend", () => loadNear(map, me));
  }

  window.initFlagsUI = function (map, socket, meUserId) {
    loadNear(map, meUserId);
    bindInteractions(map, socket, meUserId);
  };
})();
