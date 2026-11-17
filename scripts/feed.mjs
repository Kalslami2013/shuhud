// Hourly free tracker: reads environmental RSS feeds and writes data/feed.json.
// Runs on GitHub Actions; needs no AI and no Claude credit.
import { readFileSync, writeFileSync } from "node:fs";

// [name, url, language, filter]: filter true = keep only environmental stories (general news feeds); a RegExp = keep titles matching it
const FEEDS = [
  // agencies and newspapers
  ["Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "en", true],
  ["BBC", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "en", true],
  ["The Guardian", "https://www.theguardian.com/environment/rss", "en", false],
  ["Euronews", ["https://www.euronews.com/rss?level=vertical&name=green", "https://www.euronews.com/rss?format=mrss&level=vertical&name=green", "https://www.euronews.com/rss?level=theme&name=green", "https://www.euronews.com/green/rss"], "en", false],
  ["New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/Climate.xml", "en", false],
  ["Washington Post", ["https://feeds.washingtonpost.com/rss/climate-environment", "https://feeds.washingtonpost.com/rss/national/energy-environment"], "en", false],
  ["France 24 English", ["https://www.france24.com/en/environment/rss", "https://www.france24.com/en/planet/rss"], "en", false],
  ["DW", "https://rss.dw.com/rdf/rss-en-all", "en", true],
  ["Anadolu", ["https://www.aa.com.tr/en/rss/default?cat=environment", "https://www.aa.com.tr/en/rss/default?cat=guncel"], "en", true],
  ["TASS", "https://tass.com/rss/v2.xml", "en", true],
  ["UPI", ["https://rss.upi.com/news/odd_news.rss", "https://rss.upi.com/news/science_news.rss", "https://www.upi.com/rss/Odd_News/", "https://www.upi.com/rss/Science_News/"], "en", true],
  ["الجزيرة نت", "https://www.aljazeera.net/aljazeerarss/a7c186be-1baa-4bd4-9d80-a84db769f779/73d0e1b4-532f-45ef-b135-bfdff8b8cab9", "ar", true],
  ["BBC عربي", "https://feeds.bbci.co.uk/arabic/rss.xml", "ar", true],
  ["الشرق الأوسط", "https://aawsat.com/feed", "ar", true],
  ["الأناضول", "https://www.aa.com.tr/ar/rss/default?cat=guncel", "ar", true],
  ["RT عربي", ["https://arabic.rt.com/rss/", "https://arabic.rt.com/rss"], "ar", true],
  ["DW عربية", "https://rss.dw.com/rdf/rss-ar-all", "ar", true],
  ["فرانس 24", ["https://www.france24.com/ar/rss"], "ar", true],
  ["سكاي نيوز عربية", ["https://www.skynewsarabia.com/rss", "https://www.skynewsarabia.com/web/rss"], "ar", true],
  // specialised environment and science outlets
  ["Mongabay", "https://news.mongabay.com/feed/", "en", false],
  ["Inside Climate News", "https://insideclimatenews.org/feed/", "en", false],
  ["Carbon Brief", "https://www.carbonbrief.org/feed", "en", false],
  ["Yale Environment 360", "https://e360.yale.edu/feed.xml", "en", false],
  ["Climate Home News", "https://www.climatechangenews.com/feed/", "en", false],
  ["Phys.org", "https://phys.org/rss-feed/earth-news/", "en", false],
  ["Down To Earth", "https://www.downtoearth.org.in/rss/environment", "en", false],
  // UN, international and government bodies; disaster monitors
  ["UN News", "https://news.un.org/feed/subscribe/en/news/topic/climate-change/feed/rss.xml", "en", false],
  // French press and bodies (headlines translated to Arabic and English below)
  ["Le Monde", "https://www.lemonde.fr/planete/rss_full.xml", "fr", false],
  ["Reporterre", "https://reporterre.net/spip.php?page=backend", "fr", false],
  ["France 24", ["https://www.france24.com/fr/plan%C3%A8te/rss", "https://www.france24.com/fr/environnement/rss"], "fr", false],
  ["ONU Info", "https://news.un.org/feed/subscribe/fr/news/topic/climate-change/feed/rss.xml", "fr", false],
  ["أخبار الأمم المتحدة", "https://news.un.org/feed/subscribe/ar/news/topic/climate-change/feed/rss.xml", "ar", false],
  ["UNEP", ["https://www.unep.org/news-and-stories/rss.xml", "https://www.unep.org/rss/news", "https://www.unep.org/news-and-stories/press-release/rss.xml", "https://www.unep.org/rss.xml", "https://www.unep.org/feeds/news.xml"], "en", false],
  ["WMO", ["https://wmo.int/media/news/rss.xml", "https://wmo.int/news/rss.xml", "https://wmo.int/rss/news", "https://wmo.int/rss.xml", "https://wmo.int/media/rss.xml"], "en", false],
  ["WHO", "https://www.who.int/rss-feeds/news-english.xml", "en", true],
  ["FAO", ["https://www.fao.org/news/rss-feed/en/", "https://www.fao.org/newsroom/en/rss", "https://www.fao.org/rss/en/", "https://www.fao.org/newsroom/rss/en/", "https://www.fao.org/feeds/fao-newsroom-rss"], "en", true],
  ["NASA Earth Observatory", "https://earthobservatory.nasa.gov/feeds/earth-observatory.rss", "en", false],
  ["NOAA", "https://www.noaa.gov/rss.xml", "en", true],
  ["ReliefWeb", ["https://reliefweb.int/headlines/rss.xml", "https://reliefweb.int/disasters/rss.xml"], "en", false],
  ["GDACS", "https://www.gdacs.org/xml/rss.xml", "en", /\b(orange|red)\b/i],
  ["USGS", "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.atom", "en", false],
];

// general feeds keep only stories with an environmental subject, and drop market and price news unless pollution or climate is the point
const MARKET = /\b(stocks?|shares|prices?|markets?|gold|crude futures|brent|investors?)\b|أسعار|سعر|البورصة|الذهب|الأسهم|الدولار|برنت|العقود الآجلة|المستثمرين/i;
const STRONG = /spill|pollut|emission|climate|wildlife|species|flood|drought|wildfire|earthquake|تسرب|تلوث|انبعاث|مناخ|حياة برية|فيضان|جفاف|حرائق|زلزال/i;
// animal migrations, spawning, nesting and other seasonal wildlife events; "migration" counts only next to an animal
export const WILD = /(\b(birds?|crabs?|whales?|turtles?|salmon|eels?|wildebeest|zebras?|caribou|reindeer|elk|monarchs?|butterfl\w*|locusts?|bats?|storks?|cranes?|geese|flamingos?|swallows?|penguins?|seals?|sharks?|herds?|flocks?|swarms?|shoals?|animals?|wildlife|species|fish)\b.{0,40}\b(migrat\w*|spawn\w*|nesting|hatch\w*|mass crossing|journey|flyway)|\b(migrat\w*|spawn\w*|nesting season|hatching season)\b.{0,40}\b(birds?|crabs?|whales?|turtles?|salmon|eels?|wildebeest|caribou|monarchs?|butterfl\w*|storks?|cranes?|geese|flamingos?|herds?|animals?|wildlife|species|fish)|great migration|bird migration|migratory|هجرة (الطيور|الحيتان|السلاحف|الأسماك|السلمون|الحيوانات|الفراشات|السرطانات|سرطان|الحيوان|اللقالق|الكركي|النحام|الفلامنغو|الحياة البرية)|الطيور المهاجرة|الأسماك المهاجرة|موسم (التكاثر|التعشيش|الهجرة|وضع البيض)|وضع البيض|أعشاش السلاحف|migration des|oiseaux migrateurs)/i;
const KW = /climate|environment|pollut|oil spill|spill|wildfire|forest fire|deforest|flood|drought|heatwave|heat wave|cyclone|hurricane|typhoon|tornado|earthquake|tsunami|volcano|glacier|ice sheet|sea ice|coral|reef|species|extinct|wildlife|biodiversity|endangered|emission|carbon|methane|fossil fuel|renewable|landslide|\bbees?\b|pollinat|butterfl|insect|\bbirds?\b|whale|shark|turtle|poaching|desertification|air quality|smog|heat record|water crisis|water shortage|locust|bird flu|avian|ebola|cholera|el niño|el nino|unep|iucn|wmo|مناخ|بيئ|تلوث|تسرب نفطي|تسرب كيميائي|تسرب إشعاعي|حرائق|حريق غابات|غابات|فيضان|سيول|جفاف|موجة حر|حرارة قياسية|إعصار|زلزال|تسونامي|بركان|جليد|شعاب|مرجان|انقراض|حياة برية|تنوع بيولوجي|انبعاثات|كربون|ميثان|تسرب نفطي|بقعة نفطية|نحل|فراش|حشرات|طيور|حيتان|سلاحف|طاقة متجددة|انهيار أرضي|انهيارات أرضية|التصحر|تصحر|جودة الهواء|ضباب دخاني|الصيد الجائر|شح المياه|أزمة المياه|جراد|إنفلونزا الطيور|إيبولا|كوليرا|النينيو|ارتفاع البحر|ارتفاع مستوى البحر|sea level|sea-level|plastic|sewage|nurdle|rewild|nature restoration|بلاستيك|نفايات|الصرف الصحي|elephant|jaguar|reptile|tusker|wolves|wolf|\bbears?\b|lions?\b|tigers?\b|leopard|primate|gorilla|orangutan|dolphin|\bseals?\b|fisher(y|ies)|menhaden|salmon|seagrass|wetland|marsh|mangrove|forest|amazon|rainforest|\brivers?\b|\blakes?\b|delta|aquifer|groundwater|\bsoil|pesticide|toxic|contamina|sewage|tailings|geoengineer|subsidence|polar vortex|cold snap|blizzard|snowstorm|underwater|flooded|national park|habitat|ecosystem|paris agreement|global warming|warming|net zero|\bcoal\b|oil licen|drilling|fracking|logging|bushmeat|zoonotic|hantavirus|\bvirus|\bbirds?\b|heat\b|climat|biodiversit|espèce|forêt|océan|\bmer\b|rivière|fleuve|\blac\b|eau potable|pollu|pesticid|sécheresse|inondation|incendie|canicule|glacier|faune|oiseau|\bloup|\bours\b|chasse|pétrole|charbon|nucléaire|déchets|plastique|épidémie|centres? de données|data center|for[eê]t|temperature|température|cryospher|ice melt|\bice\b|fonte des glaces|banquise|glaces?\b|\bwaste|crues?\b|mégafeu|megafire|feux? de forêt|protected (area|waters)|marine|wood-burning|exhaust|riverside|\btrees?\b|arbres?\b|nuclear|reactor|planetary boundar|limite planétaire|overshoot|deep-sea|seabed|mining|everglades|pangolin|wildflower|orchid|firefl|permafrost|fossil|\bocean|tuna|tap water|eau du robinet|rockslide|protected .{0,20}waters|wildlife|faune sauvage|\bwater\b|clean energy|energy transition|fossil fuel|1\.5 ?°?c|المياه|الاحتباس الحراري|الوقود الأحفوري|الطاقة المتجددة|الطاقة النظيفة|الأمن الغذائي|الطاقة الشمسية|طاقة الرياح|التصحر|\beaux?\b|énergies? renouvelables?|fossiles?/i;
// words used as metaphors or in sport and culture headlines
const OFFTOPIC = /يحرج|إشادة|حظيت|العالم الرقمي|بق الفراش|عث الغبار|كفن|مظاهرات|يستقبل|يلتقي|تهنئة|election|elected|democrats|republicans|congress\b|lawmakers|senator|booker|novel\b|retirees|sweaters|ski lift|olympic|high streets|shared housing|far right|social movement|sit-in|protesters arrested|player|nvidia|إنفيديا|انفيديا|hockey|هوكي|football|soccer|كرة القدم|مونديال|منتخب|الدوري|جائزة|award|festival|مهرجان|\bfilm\b|فيلم|بورصة/i;
// a general-news headline must itself name the environmental subject: words in the summary alone let politics through
export const keepGeneral = (title) => (KW.test(title) || WILD.test(title) || isGood(title)) && !OFFTOPIC.test(title) && !(MARKET.test(title) && !STRONG.test(title));

// good news for nature: recoveries, rediscoveries, new reserves, rare births, reintroductions (marked "good", shown with 🌱)
export const GOOD = /comeback|rescued|saved from|is saved|sauvé|rediscover|re-discover|found alive|thought (to be )?extinct|back from (the brink|extinction)|no longer (endangered|threatened)|downlist|least concern|recover(y|ed|ing)? (of|in) (the )?(population|species)|population (rebound|recover|increase|grow)|rebound|reintroduc|rewild|returns? to the wild|released into the wild|new (marine )?(reserve|sanctuary|protected area|national park)|(creat|establish|declar|design|expand)\w* .{0,30}(protected area|reserve|sanctuary|national park)|hatchling|chicks? hatch|born in (captivity|the wild)|first (birth|calf|chick)|conservation success|restoration success|محمية (جديدة|طبيعية)|إنشاء محمية|إعادة اكتشاف|أعيد اكتشاف|ظهر(ت)? (مجددا|مجدداً|من جديد)|بعد أن (كان|كانت|اعتبر|اعتُبر)[^،.]{0,20}منقرض|عاد(ت)? إلى (البرية|الطبيعة)|إعادة (توطين|إطلاق|تأهيل)|إطلاق .{0,20}(في البرية|في الطبيعة)|تعافي (أعداد|الشعاب|المرجان|الغابات|الغابة|البحيرة|النهر|الأنواع|الحياة البرية|طبقة الأوزون)|ولادة (نادرة|صغير|أول)|فقس|خرج(ت)? من (قائمة|خطر)|réintrodu|aire (marine )?protégée|réserve naturelle|redécouv|naissance|retour (du|de la|des)|rétablissement|sauvé/i;
const NOT_GOOD = /إصابة|injur|match|tennis|football|كرة|مباراة|fail|failing|loss|lose|losing|declin|threat|collapse|open\w* .{0,30}to (fishing|mining|drilling|logging)|roll ?back|يفشل|تفشل|تراجع|تهديد|خسارة|échec|menac|recul/i;
export const isGood = (t) => GOOD.test(t) && !NOT_GOOD.test(t);
const CAT = [
    ["التلوث", /pollut|spill|plastic|تلوث|تسرب|نفايات/i],
  ["الحروب والبيئة", /war|strike|attack|missile|drone|حرب|غارة|قصف|هجوم|مسيّرة/i],
  ["التقنية والذكاء الاصطناعي", /data cent|\bai\b|artificial intel|مراكز البيانات|ذكاء اصطناعي/i],
  ["الغابات", /forest|deforest|wildfire|غابات|حرائق/i],
  ["البحار والمحيطات", /ocean|sea\b|coral|reef|marine|بحر|محيط|شعاب|مرجان/i],
  ["المياه", /water|river|dam|drought|مياه|نهر|سد|جفاف/i],
  ["كوارث طبيعية", /flood|cyclone|hurricane|typhoon|storm|earthquake|tsunami|volcano|فيضان|سيول|إعصار|عاصفة|زلزال|بركان/i],
  ["الميكروبات والأوبئة", /virus|outbreak|flu|ebola|disease|epidemic|فيروس|تفشي|وباء|إنفلونزا|إيبولا/i],
  ["الهجرة والنزوح", WILD],
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

const TRUSTED = new Set(["GDACS", "USGS", "ReliefWeb", "NASA Earth Observatory", "UNEP", "WMO", "NOAA"]);
export function parse(xml, [source, , lang, filter]) {
  const blocks = xml.match(/<item[\s>][\s\S]*?<\/item>|<entry[\s>][\s\S]*?<\/entry>/gi) || [];
  return blocks.map((b) => {
    const title = tag(b, "title"), url = link(b).trim(), summary = tag(b, "description") || tag(b, "summary");
    const when = tag(b, "pubDate") || tag(b, "published") || tag(b, "updated") || tag(b, "dc:date");
    const d = new Date(when); const at = isNaN(d) ? new Date().toISOString() : d.toISOString();
    if (!title || !url) return null;
    const txt = title + " " + summary;
    // every outlet must name a subject of the platform in the headline itself; disaster monitors and science agencies are trusted as they are
    if (filter instanceof RegExp ? !filter.test(title) : !TRUSTED.has(source) && !keepGeneral(title)) return null;
    const category = CAT.find(([, re]) => re.test(title + " " + summary))[0];
    const item = { id: "r-" + hash(url), at, date: at.slice(0, 10), text: title, source, url, category, lang, rss: true, createdAt: new Date().toISOString() };
    if (isGood(title)) { item.good = true; item.category = "الطبيعة تتعافى"; }
    if (lang === "en") item.en = { text: title, source };
    return item;
  }).filter(Boolean);
}

async function main() {
  const path = "data/feed.json";
  let old = []; try { old = JSON.parse(readFileSync(path, "utf8")); } catch {}
  // stored headlines from general feeds are checked again, so a looser earlier rule leaves nothing behind
  old = old.filter((x) => TRUSTED.has(x.source) || keepGeneral(x.text));
  for (const x of old) { if (isGood(x.text)) { x.good = true; x.category = "الطبيعة تتعافى"; } else delete x.good; }
  const seen = new Map(old.map((x) => [x.id, x]));
  const norm = (t) => t.toLowerCase().replace(/[^\p{L}\p{N} ]/gu, "").slice(0, 80);
  const titles = new Set(old.map((x) => norm(x.text)));
  const cutoff = Date.now() - 3 * 864e5;
  let added = 0;
  for (const f of FEEDS) {
    try {
      // a source may list several addresses: the first that answers is used
      let r = null;
      for (const u of [].concat(f[1])) {
        try { r = await fetch(u, { headers: { "user-agent": "Mozilla/5.0 (compatible; ShuhudTracker/1.0; +https://alshuhud.org)", accept: "application/rss+xml, application/atom+xml, application/xml, text/xml, */*" }, signal: AbortSignal.timeout(20000) }); } catch { r = null; }
        if (r && r.ok) break;
      }
      if (!r || !r.ok) { console.log("skip", f[0], r && r.status); continue; }
      const items = parse(await r.text(), f).filter((x) => new Date(x.at) > cutoff);
      for (const it of items) { const n = norm(it.text); if (seen.has(it.id) || titles.has(n)) continue; seen.set(it.id, it); titles.add(n); added++; }
      console.log("ok", f[0], items.length);
    } catch (e) { console.log("fail", f[0], e.message); }
  }
  // English and French headlines get an Arabic translation, French ones an English one too (free endpoints; skipped quietly if unavailable)
  let tr = 0; const trLog = [];
  const gtx = async (q, sl, tl) => { const r = await fetch(`https://translate.googleapis.com/translate_a/single?client=gtx&sl=${sl}&tl=${tl}&dt=t&q=` + encodeURIComponent(q), { headers: { "user-agent": "Mozilla/5.0" }, signal: AbortSignal.timeout(10000) }); if (!r.ok) throw new Error("gtx " + r.status); const j = await r.json(); return (j[0] || []).map((x) => x[0]).join("").trim(); };
  const mym = async (q, sl, tl) => { const r = await fetch(`https://api.mymemory.translated.net/get?langpair=${sl}|${tl}&q=` + encodeURIComponent(q.slice(0, 480)), { signal: AbortSignal.timeout(10000) }); if (!r.ok) throw new Error("mymemory " + r.status); const j = await r.json(); const t = j?.responseData?.translatedText || ""; if (/MYMEMORY WARNING|QUERY LENGTH/i.test(t)) throw new Error("mymemory quota"); return t.trim(); };
  let engines = [gtx, mym];
  const translate = async (q, sl, tl) => { for (const eng of [...engines]) { try { const t = await eng(q, sl, tl); if (t) return t; } catch (e) { trLog.push(e.message); engines = engines.filter((x) => x !== eng); } } return ""; };
  for (const it of seen.values()) {
    if (it.lang === "ar" || tr >= 100 || !engines.length) continue;
    if (!it.trAr) { const t = await translate(it.text, it.lang, "ar"); if (t) { it.trAr = t; tr++; } await new Promise((ok) => setTimeout(ok, 300)); }
    if (it.lang === "fr" && !it.trEn && engines.length) { const t = await translate(it.text, "fr", "en"); if (t) { it.trEn = t; tr++; } await new Promise((ok) => setTimeout(ok, 300)); }
  }
  writeFileSync("data/feed-status.json", JSON.stringify({ at: new Date().toISOString(), translated: tr, errors: trLog.slice(0, 5) }));
  console.log("translated", tr);
  const all = [...seen.values()].sort((a, b) => (a.at < b.at ? 1 : -1)).slice(0, 500);
  writeFileSync(path, JSON.stringify(all));
  console.log("added", added, "total", all.length);
}
if (process.argv[1] && process.argv[1].endsWith("feed.mjs")) main();
