// Live alerts for the Shuhud Atlas (data/alerts.json): natural hazards with coordinates,
// from three free public feeds. Runs inside the hourly feed workflow; it does not use Claude.
//   GDACS (UN/EU Global Disaster Alert and Coordination System): cyclones, floods, droughts, volcanoes, wildfires
//   USGS: earthquakes of magnitude 5.5 and above, past week
//   NASA EONET: open natural events (wildfires, volcanoes, storms, ice, dust), past 30 days
import { writeFileSync } from "node:fs";

const UA = { "user-agent": "ShuhudAtlas/1.0 (+https://alshuhud.org)" };
const get = async (u, kind = "text") => {
  const r = await fetch(u, { headers: UA, signal: AbortSignal.timeout(40000) });
  if (!r.ok) throw new Error(u + " " + r.status);
  return kind === "json" ? r.json() : r.text();
};
const TYPE_AR = { EQ: "زلزال", TC: "إعصار مداري", FL: "فيضان", DR: "جفاف", VO: "بركان", WF: "حرائق غابات", ST: "عاصفة", ICE: "جليد بحري", DUST: "عاصفة ترابية" };
const TYPE_EN = { EQ: "Earthquake", TC: "Tropical cyclone", FL: "Flood", DR: "Drought", VO: "Volcano", WF: "Wildfire", ST: "Storm", ICE: "Sea ice", DUST: "Dust storm" };
const LEVEL_AR = { red: "إنذار أحمر", orange: "إنذار برتقالي", green: "إنذار أخضر" };
const round = (v) => Math.round(v * 100) / 100;
const out = [];
const errors = [];

// ---------- GDACS (RSS with geo:lat / geo:long) ----------
try {
  const xml = await get("https://www.gdacs.org/xml/rss.xml");
  const tag = (s, t) => { const m = s.match(new RegExp(`<${t}[^>]*>([\\s\\S]*?)</${t}>`)); return m ? m[1].replace(/<!\[CDATA\[|\]\]>/g, "").trim() : ""; };
  const now = Date.now();
  for (const it of xml.split("<item>").slice(1)) {
    const type = tag(it, "gdacs:eventtype").toUpperCase();
    if (!TYPE_AR[type] || type === "EQ") continue; // earthquakes come from USGS
    const level = tag(it, "gdacs:alertlevel").toLowerCase();
    const lat = parseFloat(tag(it, "geo:lat")), lon = parseFloat(tag(it, "geo:long"));
    if (!isFinite(lat) || !isFinite(lon)) continue;
    const cur = tag(it, "gdacs:iscurrent").toLowerCase() === "true";
    const to = Date.parse(tag(it, "gdacs:todate")) || Date.parse(tag(it, "pubDate")) || now;
    if (!cur && now - to > 14 * 864e5) continue;
    if (level === "green" && type !== "DR" && type !== "VO") continue; // keep green only for slow hazards
    const name = tag(it, "gdacs:eventname");
    const country = tag(it, "gdacs:country");
    const title = tag(it, "title");
    out.push({
      id: "g-" + tag(it, "gdacs:eventid") + "-" + type, src: "GDACS", type, level, lat: round(lat), lon: round(lon),
      at: new Date(Date.parse(tag(it, "pubDate")) || to).toISOString(), url: tag(it, "link"), country,
      en: `${TYPE_EN[type]}${name ? " " + name : ""}${country ? " · " + country : ""}`,
      ar: `${TYPE_AR[type]}${name ? " " + name : ""}${country ? " · " + country : ""}${LEVEL_AR[level] ? " · " + LEVEL_AR[level] : ""}`,
      detail: title,
    });
  }
} catch (e) { errors.push("gdacs: " + e.message); }

// ---------- USGS earthquakes M5.5+ ----------
try {
  const j = await get("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson", "json");
  for (const f of j.features || []) {
    const p = f.properties || {}, c = (f.geometry || {}).coordinates || [];
    if (!(p.mag >= 5.5) || c.length < 2) continue;
    const level = p.alert || (p.mag >= 7 ? "red" : p.mag >= 6.5 ? "orange" : "green");
    out.push({
      id: "u-" + f.id, src: "USGS", type: "EQ", level, mag: p.mag, lat: round(c[1]), lon: round(c[0]),
      at: new Date(p.time).toISOString(), url: p.url, country: (p.place || "").split(",").pop().trim(),
      en: `Earthquake M${p.mag} · ${p.place || ""}`, ar: `زلزال بقوة ${p.mag} · ${p.place || ""}`, detail: p.title || "",
    });
  }
} catch (e) { errors.push("usgs: " + e.message); }

// ---------- NASA EONET open events ----------
try {
  const j = await get("https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=30", "json");
  const CAT = { wildfires: "WF", volcanoes: "VO", severeStorms: "ST", dustHaze: "DUST", floods: "FL", drought: "DR" }; // icebergs (seaLakeIce) are not crises
  const gdacsNames = out.filter((x) => x.src === "GDACS").map((x) => (x.en || "").toLowerCase());
  let fires = 0;
  for (const ev of j.events || []) {
    const type = CAT[(ev.categories || [])[0]?.id];
    if (!type) continue;
    const g = (ev.geometry || []).slice(-1)[0];
    if (!g) continue;
    let pt = g.coordinates;
    if (g.type === "Polygon") { const ring = pt[0]; pt = [ring.reduce((a, q) => a + q[0], 0) / ring.length, ring.reduce((a, q) => a + q[1], 0) / ring.length]; }
    if (!Array.isArray(pt) || pt.length < 2) continue;
    const title = String(ev.title || "");
    if (/prescribed|\bRX\b/i.test(title)) continue; // planned burns are not crises
    if (type === "ST" && gdacsNames.some((n) => title.toLowerCase().split(/\s+/).slice(-1)[0] && n.includes(title.toLowerCase().split(/\s+/).slice(-1)[0]))) continue;
    if (type === "WF" && ++fires > 40) continue;
    out.push({
      id: "e-" + ev.id, src: "NASA EONET", type, level: type === "VO" || type === "ST" ? "orange" : "green", lat: round(pt[1]), lon: round(pt[0]),
      at: new Date(g.date || Date.now()).toISOString(), url: ev.sources?.[0]?.url || ev.link, country: "",
      en: title, ar: /^tropical (cyclone|storm)|^typhoon|^hurricane/i.test(title) ? `إعصار مداري ${title.replace(/^(super )?(tropical (cyclone|storm)|typhoon|hurricane)\s*/i, "")}` : /wildfire|fire/i.test(title) ? `حرائق غابات · ${title.replace(/\s*(wild)?fire\b/i, "").trim()}` : `${TYPE_AR[type]} · ${title}`, detail: "",
    });
  }
} catch (e) { errors.push("eonet: " + e.message); }

out.sort((a, b) => (b.at > a.at ? 1 : -1));
writeFileSync("data/alerts.json", JSON.stringify({ at: new Date().toISOString(), errors, items: out }));
console.log("alerts", out.length, errors.join(" | "));
