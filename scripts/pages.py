# Builds one public page per piece (p/<id>.html), the archive (p/index.html) and sitemap.xml,
# from data/pieces.json + data/pieces-gh.json, so Google can index each piece on its own.
# Run from the repo root: python3 scripts/pages.py   (the GitHub workflow pages.yml runs it on every data change)
import json, os, re, html, glob, datetime

BASE = "https://alshuhud.org/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

def load(f):
    try:
        with open(f, encoding="utf8") as fh:
            d = json.load(fh)
        return d if isinstance(d, list) else []
    except Exception:
        return []

pieces = {}
for f in ("data/pieces.json", "data/pieces-gh.json"):
    for p in load(f):
        if isinstance(p, dict) and p.get("id"):
            pieces[p["id"]] = {**pieces.get(p["id"], {}), **p}
pieces = {k: v for k, v in pieces.items() if v.get("headline")}
species = {}
for s in load("data/species.json"):
    for k in (s.get("id"), s.get("key")):
        if k:
            species[k] = s

ICONS = json.load(open("scripts/social_icons.json", encoding="utf8"))
ORDER = ["x","facebook","instagram","youtube","tiktok","telegram","whatsapp","linkedin","threads","bluesky","email","web"]
socials = [x for f in ("data/partners.json", "data/partners-gh.json") for x in load(f) if isinstance(x, dict) and x.get("type") == "social" and x.get("url")]
socials.sort(key=lambda x: (ORDER.index(x.get("platform")) if x.get("platform") in ORDER else 99, str(x.get("createdAt") or "")))
def href(x):
    u = str(x["url"]).strip()
    if x.get("platform") == "email" and not u.lower().startswith("mailto:"): return "mailto:" + u
    return u if re.match(r"^(https?:|mailto:)", u, re.I) else "https://" + u

e = lambda s: html.escape(str(s or ""), quote=True)
SAFE = re.compile(r"^[A-Za-z0-9_-]{1,120}$")

def date_of(p):
    for k in ("eventDate", "createdAt"):
        v = str(p.get(k) or "")
        if re.match(r"\d{4}-\d{2}-\d{2}", v):
            return v[:10]
    return ""

def image_of(p):
    u = str(p.get("imageUrl") or "")
    if u.startswith("http"):
        return u, p.get("imageCredit") or ""
    if u.startswith("/_blob/"):
        u = "media/" + re.sub(r"[^\w-]", "", u[7:]) + ".jpg"
    if u.startswith("media/") and os.path.exists(u):
        return BASE + u, p.get("imageCredit") or ""
    s = species.get(p.get("animal"))
    if s and str(s.get("extImg") or "").startswith("http"):
        return s["extImg"], s.get("credit") or ""
    return "", ""

AR_MONTHS = ["يناير","فبراير","مارس","أبريل","مايو","يونيو","يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"]
EN_MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"]
def nice(d, ar=True):
    try:
        y, m, dd = d.split("-")
        return f"{int(dd)} {(AR_MONTHS if ar else EN_MONTHS)[int(m)-1]} {y}"
    except Exception:
        return d

def short(s, n=158):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"

CSS = """:root{--bg:#0b1712;--card:#12241c;--ink:#e8efe9;--mute:#9fb3a7;--acc:#7fd1a0;--line:#21392d}
@media (prefers-color-scheme:light){:root{--bg:#f4f1ea;--card:#fff;--ink:#17231c;--mute:#5d6d63;--acc:#1f7a4b;--line:#e1ddd2}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.85 "Noto Naskh Arabic","Segoe UI",Tahoma,system-ui,sans-serif}
a{color:var(--acc)}.wrap{max-width:760px;margin:0 auto;padding:0 16px}
header.top{border-bottom:1px solid var(--line);padding:14px 0}header.top .wrap{display:flex;justify-content:space-between;align-items:center;gap:12px}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--ink);font-weight:700;font-size:20px}.brand img{width:34px;height:34px;border-radius:8px}
.top nav a{font-size:15px;text-decoration:none;margin-inline-start:14px}
article{padding:26px 0 10px}.kick{color:var(--acc);font-size:14px;font-weight:600}.meta{color:var(--mute);font-size:14px;margin:6px 0 18px}
h1{font-size:30px;line-height:1.4;margin:6px 0}h2{font-size:21px;margin:28px 0 8px}
figure{margin:0 0 18px}figure img{display:block;max-width:100%;max-height:520px;margin:0 auto;border-radius:12px}figcaption{color:var(--mute);font-size:12px;text-align:center;margin-top:4px}
.voice{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;white-space:pre-line}
.angle{font-size:19px;color:var(--mute)}.figs{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.fig{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}.fig b{display:block;font-size:22px;color:var(--acc)}.fig small{color:var(--mute)}
ul{padding-inline-start:22px}.q{border-inline-start:4px solid var(--acc);padding:4px 14px;font-style:italic}
.en{direction:ltr;text-align:left;font-family:Georgia,"Segoe UI",system-ui,serif;border-top:1px solid var(--line);margin-top:34px}
.cta{display:inline-block;background:var(--acc);color:var(--bg);text-decoration:none;padding:10px 18px;border-radius:999px;font-weight:700;margin:20px 0}
footer{border-top:1px solid var(--line);color:var(--mute);font-size:14px;padding:18px 0 40px;margin-top:30px}
.list{list-style:none;padding:0}.list li{border-bottom:1px solid var(--line);padding:14px 0}.list a{text-decoration:none;color:var(--ink);font-weight:700;font-size:19px}.list small{display:block;color:var(--mute)}
.sc{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 12px}.sc a{width:40px;height:40px;border-radius:50%;display:grid;place-items:center;background:var(--card);border:1px solid var(--line);color:var(--ink)}.sc svg{width:19px;height:19px;fill:currentColor}"""

def head(title, desc, url, img, extra=""):
    img = img or BASE + "og.jpg"
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{e(url)}"><meta name="robots" content="index,follow,max-image-preview:large">
<meta name="theme-color" content="#0b1712"><link rel="icon" href="{BASE}favicon.ico" sizes="48x48"><link rel="icon" type="image/png" sizes="96x96" href="{BASE}icon-96.png"><link rel="icon" type="image/png" sizes="192x192" href="{BASE}icon-192.png"><link rel="apple-touch-icon" href="{BASE}icon-180.png">
<meta property="og:site_name" content="شهود · Shuhud"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{e(url)}"><meta property="og:image" content="{e(img)}"><meta property="og:locale" content="ar_AR"><meta property="og:locale:alternate" content="en_GB">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{e(img)}">
{extra}<style>{CSS}</style></head><body>
<header class="top"><div class="wrap"><a class="brand" href="{BASE}"><img src="{BASE}icon-192.png" alt="">شهود</a><nav><a href="{BASE}p/">كل القطع</a><a href="{BASE}#about">من نحن</a></nav></div></header>
"""

SC = ('<div class="sc">' + "".join(f'<a href="{e(href(x))}" target="_blank" rel="noopener me" title="{e(x.get("name") or x.get("platform"))}" aria-label="{e(x.get("name") or x.get("platform"))}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="{ICONS.get(x.get("platform"), ICONS["web"])}"/></svg></a>' for x in socials) + "</div>") if socials else ""
FOOT = f"""<footer><div class="wrap">{SC}شهود · Shuhud — أزمات العالم بلسان الكائنات التي تعيشها. <a href="{BASE}">alshuhud.org</a></div></footer>
</body></html>
"""

def block(p, ar=True):
    t = (lambda a, b: a if ar else b)
    out = []
    if p.get("angle"): out.append(f'<p class="angle">{e(p["angle"])}</p>')
    if p.get("dispatch"):
        out.append(f'<h2>{t("شهادة " + e(p.get("animalName")), "Testimony of the " + e(p.get("animalName")))}</h2><div class="voice">{e(p["dispatch"])}</div>')
    if p.get("fact"): out.append(f'<h2>{t("ما حدث","What happened")}</h2><p>{e(p["fact"])}</p>')
    figs = [f for f in (p.get("figures") or []) if isinstance(f, dict) and f.get("value")]
    if figs:
        out.append(f'<h2>{t("بالأرقام","In numbers")}</h2><div class="figs">' + "".join(
            f'<div class="fig"><b>{e(f.get("value"))}</b>{e(f.get("label"))}<br><small>{e(f.get("source"))}</small></div>' for f in figs) + "</div>")
    imps = [i for i in (p.get("impacts") or []) if isinstance(i, str) and i.strip()]
    if imps: out.append(f'<h2>{t("سلسلة الأثر","Chain of impact")}</h2><ul>' + "".join(f"<li>{e(i)}</li>" for i in imps) + "</ul>")
    if p.get("question"): out.append(f'<h2>{t("سؤال مفتوح","Open question")}</h2><p class="q">{e(p["question"])}</p>')
    srcs = [s for s in (p.get("sources") or []) if isinstance(s, dict) and s.get("name")]
    if srcs:
        out.append(f'<h2>{t("المصادر","Sources")}</h2><ul>' + "".join(
            (f'<li><a href="{e(s["url"])}" rel="nofollow noopener" target="_blank">{e(s["name"])}</a></li>' if str(s.get("url") or "").startswith("http") else f'<li>{e(s["name"])}</li>') for s in srcs) + "</ul>")
    return "\n".join(out)

os.makedirs("p", exist_ok=True)
built = set()
items = sorted(pieces.values(), key=lambda p: (date_of(p), str(p.get("createdAt") or "")), reverse=True)
for p in items:
    pid = p["id"]
    if not SAFE.match(pid):
        continue
    url = f"{BASE}p/{pid}.html"
    d = date_of(p)
    img, credit = image_of(p)
    en = p.get("en") if isinstance(p.get("en"), dict) else {}
    title = f'{p["headline"]} | شهود'
    desc = short(p.get("angle") or p.get("fact") or p.get("dispatch"))
    ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": short(p["headline"], 110),
          "description": desc, "inLanguage": ["ar", "en"] if en else "ar", "mainEntityOfPage": url,
          "author": {"@type": "Person", "name": "Kamal Al-Salami", "alternateName": "كمال السلامي"},
          "publisher": {"@type": "NewsMediaOrganization", "name": "شهود", "alternateName": "Shuhud", "url": BASE, "logo": {"@type": "ImageObject", "url": BASE + "icon-512.png"}}}
    if d: ld["datePublished"] = str(p.get("createdAt") or d)[:25]
    if img: ld["image"] = [img]
    if en.get("headline"): ld["alternativeHeadline"] = short(en["headline"], 110)
    extra = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
    kick = " · ".join(x for x in (e(p.get("category")), e(p.get("place"))) if x)
    body = [head(title, desc, url, img, extra), '<main class="wrap"><article>']
    body.append(f'<div class="kick">{p.get("animalEmoji","")} {e(p.get("animalName"))}{" · " + kick if kick else ""}</div>')
    body.append(f'<h1>{e(p["headline"])}</h1><div class="meta">{nice(d) if d else ""}{" · " if d else ""}{e(p.get("crisis"))}</div>')
    if img:
        body.append(f'<figure><img src="{e(img)}" alt="{e(p.get("animalName"))}" loading="eager">{f"<figcaption>{e(credit)}</figcaption>" if credit else ""}</figure>')
    body.append(block(p, True))
    if en.get("headline"):
        en_full = {**en, "figures": en.get("figures") or [], "sources": en.get("sources") or p.get("sources")}
        body.append(f'<section class="en" lang="en" dir="ltr"><h1>{e(en["headline"])}</h1><div class="meta">{nice(d, False) if d else ""}{" · " if d else ""}{e(en.get("crisis"))}</div>{block(en_full, False)}</section>')
    body.append(f'<a class="cta" href="{BASE}">اقرأ المزيد في شهود ←</a></article></main>')
    body.append(FOOT)
    with open(f"p/{pid}.html", "w", encoding="utf8") as fh:
        fh.write("\n".join(body))
    built.add(pid)

# pages of pieces that were deleted are removed
for f in glob.glob("p/*.html"):
    n = os.path.basename(f)[:-5]
    if n != "index" and n not in built:
        os.remove(f)

# archive
rows = []
for p in items:
    if p["id"] not in built: continue
    d = date_of(p)
    rows.append(f'<li><a href="{p["id"]}.html">{e(p["headline"])}</a><small>{p.get("animalEmoji","")} {e(p.get("animalName"))} · {nice(d) if d else ""}</small></li>')
arch = head("كل القطع | شهود — أزمات العالم بلسان الكائنات التي تعيشها",
            "أرشيف قطع شهود: أزمات العالم من زاويتها البيئية بلسان الكائنات التي تعيشها، بالعربية والإنجليزية.", BASE + "p/", "")
with open("p/index.html", "w", encoding="utf8") as fh:
    fh.write(arch + f'<main class="wrap"><article><h1>كل القطع</h1><div class="meta">{len(rows)} قطعة</div><ul class="list">' + "\n".join(rows) + "</ul></article></main>" + FOOT)

# sitemap
today = datetime.date.today().isoformat()
urls = [f"  <url><loc>{BASE}</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>",
        f"  <url><loc>{BASE}p/</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>0.8</priority></url>"]
for p in items:
    if p["id"] in built:
        d = date_of(p) or today
        urls.append(f"  <url><loc>{BASE}p/{p['id']}.html</loc><lastmod>{d}</lastmod><priority>0.7</priority></url>")
with open("sitemap.xml", "w", encoding="utf8") as fh:
    fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n")
print(len(built), "piece pages")
