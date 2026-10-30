// Hourly free tracker: reads environmental RSS feeds and writes data/feed.json.
// Runs on GitHub Actions; needs no AI and no Claude credit.
import { readFileSync, writeFileSync } from "node:fs";

const FEEDS = [
  ["Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "en", true],
  ["BBC", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "en", false],
  ["The Guardian", "https://www.theguardian.com/environment/rss", "en", false],
  ["Mongabay", "https://news.mongabay.com/feed/", "en", false],
  ["Inside Climate News", "https://insideclimatenews.org/feed/", "en", false],
  ["UN News", "https://news.un.org/feed/subscribe/en/news/topic/climate-change/feed/rss.xml", "en", false],
  ["Euronews", "https://www.euronews.com/rss?level=vertical&name=green", "en", false],
  ["NASA Earth Observatory", "https://earthobservatory.nasa.gov/feeds/earth-observatory.rss", "en", false],
  ["الجزيرة نت", "https://www.aljazeera.net/aljazeerarss/a7c186be-1baa-4bd4-9d80-a84db769f779/73d0e1b4-532f-45ef-b135-bfdff8b8cab9", "ar", true],
  ["BBC عربي", "https://feeds.bbci.co.uk/arabic/rss.xml", "ar", true],
  ["الشرق الأوسط", "https://aawsat.com/feed", "ar", true],
  ["الأناضول", "https://www.aa.com.tr/ar/rss/default?cat=guncel", "ar", true],
];

// general feeds keep only stories with an environmental subject
const KW = /climate|environment|pollut|oil spill|spill|wildfire|forest fire|deforest|flood|drought|heatwave|heat wave|cyclone|hurricane|typhoon|storm|earthquake|tsunami|volcano|glacier|ice sheet|sea ice|coral|reef|ocean|species|extinct|wildlife|biodiversity|endangered|emission|carbon|methane|fossil|renewable|data cent|water crisis|water shortage|famine|locust|bird flu|avian|ebola|outbreak|el niño|el nino|cop31|cop17|unep|iucn|wmo|مناخ|بيئ|تلوث|تسرب|حرائق|حريق غابات|غابات|فيضان|فيضانات|سيول|جفاف|موجة حر|إعصار|عاصفة|زلزال|تسونامي|بركان|جليد|شعاب|مرجان|انقراض|حياة برية|تنوع بيولوجي|انبعاثات|كربون|ميثان|نفط|طاقة متجددة|مراكز البيانات|شح المياه|أزمة المياه|مجاعة|جراد|إنفلونزا الطيور|إيبولا|تفشي|النينيو|التصحر|كوب31/i;

const CAT = [
  ["التلوث", /pollut|spill|plastic|تلوث|تسرب|نفايات/i],
  ["الحروب والبيئة", /war|strike|attack|missile|drone|حرب|غارة|قصف|هجوم|مسيّرة/i],
  ["التقنية والذكاء الاصطناعي", /data cent|\bai\b|artificial intel|مراكز البيانات|ذكاء اصطناعي/i],
  ["الغابات", /forest|deforest|wildfire|غابات|حرائق/i],
  ["البحار والمحيطات", /ocean|sea\b|coral|reef|marine|بحر|محيط|شعاب|مرجان/i],
  ["المياه", /water|river|dam|drought|مياه|نهر|سد|جفاف/i],
  ["كوارث طبيعية", /flood|cyclone|hurricane|typhoon|storm|earthquake|tsunami|volcano|فيضان|سيول|إعصار|عاصفة|زلزال|بركان/i],
  ["الميكروبات والأوبئة", /virus|outbreak|flu|ebola|disease|epidemic|فيروس|تفشي|وباء|إنفلونزا|إيبولا/i],
  ["الانقراض", /species|extinct|wildlife|biodiversity|endangered|انقراض|حياة برية|تنوع بيولوجي/i],
  ["الطاقة", /energy|oil|gas|coal|solar|wind power|renewable|طاقة|نفط|غاز|فحم/i],
  ["الغذاء والزراعة", /food|crop|farm|harvest|famine|locust|غذاء|محاصيل|زراعة|مجاعة|جراد/i],
  ["الهجرة والنزوح", /refugee|displac|migrat|لاجئ|نزوح|نازح/i],
  ["الكون", /space|nasa|asteroid|solar storm|فضاء|كويكب/i],
  ["المناخ", /.*/],
];

const decode = (s) => String(s || "")
  .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1").replace(/<[^>]+>/g, " ")
  .replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'")
  .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(+n)).replace(/\s+/g, " ").trim();
const tag = (block, name) => { const m = block.match(new RegExp(`<${name}[^>]*>([\\s\\S]*?)</${name}>`, "i")); return m ? decode(m[1]) : ""; };
const link = (block) => { const a = block.match(/<link[^>]*href="([^"]+)"/i); return a ? a[1] : tag(block, "link"); };
const hash = (s) => { let h = 5381; for (const c of s) h = ((h << 5) + h + c.charCodeAt(0)) | 0; return (h >>> 0).toString(36); };

export function parse(xml, [source, , lang, filter]) {
  const blocks = xml.match(/<item[\s>][\s\S]*?<\/item>|<entry[\s>][\s\S]*?<\/entry>/gi) || [];
  return blocks.map((b) => {
    const title = tag(b, "title"), url = link(b).trim(), summary = tag(b, "description") || tag(b, "summary");
    const when = tag(b, "pubDate") || tag(b, "published") || tag(b, "updated") || tag(b, "dc:date");
    const d = new Date(when); const at = isNaN(d) ? new Date().toISOString() : d.toISOString();
    if (!title || !url) return null;
    if (filter && !KW.test(title + " " + summary)) return null;
    const category = CAT.find(([, re]) => re.test(title + " " + summary))[0];
    const item = { id: "r-" + hash(url), at, date: at.slice(0, 10), text: title, source, url, category, lang, rss: true, createdAt: new Date().toISOString() };
    if (lang === "en") item.en = { text: title, source };
    return item;
  }).filter(Boolean);
}

async function main() {
  const path = "data/feed.json";
  let old = []; try { old = JSON.parse(readFileSync(path, "utf8")); } catch {}
  const seen = new Map(old.map((x) => [x.id, x]));
  const norm = (t) => t.toLowerCase().replace(/[^\p{L}\p{N} ]/gu, "").slice(0, 80);
  const titles = new Set(old.map((x) => norm(x.text)));
  const cutoff = Date.now() - 3 * 864e5;
  let added = 0;
  for (const f of FEEDS) {
    try {
      const r = await fetch(f[1], { headers: { "user-agent": "Mozilla/5.0 (Shuhud tracker)" }, signal: AbortSignal.timeout(20000) });
      if (!r.ok) { console.log("skip", f[0], r.status); continue; }
      const items = parse(await r.text(), f).filter((x) => new Date(x.at) > cutoff);
      for (const it of items) { const n = norm(it.text); if (seen.has(it.id) || titles.has(n)) continue; seen.set(it.id, it); titles.add(n); added++; }
      console.log("ok", f[0], items.length);
    } catch (e) { console.log("fail", f[0], e.message); }
  }
  // English headlines also get an Arabic translation (free Google endpoint; skipped quietly if unavailable)
  let tr = 0;
  for (const it of seen.values()) {
    if (it.lang !== "en" || it.trAr || tr >= 80) continue;
    try {
      const r = await fetch("https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ar&dt=t&q=" + encodeURIComponent(it.text), { signal: AbortSignal.timeout(10000) });
      if (!r.ok) { console.log("translate", r.status); break; }
      const j = await r.json(); const ar = (j[0] || []).map((x) => x[0]).join("").trim();
      if (ar) { it.trAr = ar; tr++; }
      await new Promise((ok) => setTimeout(ok, 250));
    } catch (e) { console.log("translate fail", e.message); break; }
  }
  console.log("translated", tr);
  const all = [...seen.values()].sort((a, b) => (a.at < b.at ? 1 : -1)).slice(0, 400);
  writeFileSync(path, JSON.stringify(all));
  console.log("added", added, "total", all.length);
}
if (process.argv[1] && process.argv[1].endsWith("feed.mjs")) main();
