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
    for k in ("createdAt", "eventDate"):  # the date shown is the day the piece was published
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
    # species written for one story (animal "custom") have no card: borrow the photo of its Wikipedia article
    en = p.get("en") if isinstance(p.get("en"), dict) else {}
    name = str(en.get("animalName") or "").strip()
    if name:
        img = wiki_image(name)
        if img:
            return img, "Wikipedia"
    return "", ""

def narr_of(p):
    """the narrator's own photo, shown in a small circle when the piece has a photo of the event"""
    if not str(p.get("imageUrl") or ""): return ""
    s = species.get(p.get("animal"))
    if s and str(s.get("extImg") or "").startswith("http"): return s["extImg"]
    en = p.get("en") if isinstance(p.get("en"), dict) else {}
    name = str(en.get("animalName") or "").strip()
    return wiki_image(name) if name else ""

WIKI_PATH = "data/wiki-img.json"
try:
    WIKI = json.load(open(WIKI_PATH, encoding="utf8"))
except Exception:
    WIKI = {}
def wiki_image(name):
    if name in WIKI and "/640px-" not in WIKI[name]:
        return WIKI[name].split("?")[0].replace("://thumb.wikimedia.org/", "://upload.wikimedia.org/")
    import urllib.request, urllib.parse
    url = ""
    try:
        req = urllib.request.Request("https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(name.replace(" ", "_")),
                                     headers={"user-agent": "ShuhudPages/1.0 (https://alshuhud.org)"})
        with urllib.request.urlopen(req, timeout=8) as r:
            j = json.load(r)
        t = (j.get("thumbnail") or {}).get("source") or ""
        o = j.get("originalimage") or {}
        if t and j.get("type") != "disambiguation":
            url = re.sub(r"/\d+px-", "/960px-", t) if (o.get("width") or 0) > 960 and "/thumb/" in t else (o.get("source") or t)
            url = url.split("?")[0].replace("://thumb.wikimedia.org/", "://upload.wikimedia.org/")
    except Exception:
        return ""  # not cached: try again next build
    WIKI[name] = url
    return url

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
figure{margin:0 0 18px;position:relative}figure .narr{position:absolute;right:12px;bottom:34px;width:20%;max-width:104px;min-width:52px;aspect-ratio:1;border-radius:50%;object-fit:cover;border:3px solid #f4efe2;box-shadow:0 4px 16px rgba(0,0,0,.55)}figure img{display:block;max-width:100%;max-height:520px;margin:0 auto;border-radius:12px}figcaption{color:var(--mute);font-size:12px;text-align:center;margin-top:4px}
.voice{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px}.voice p{margin:0 0 1em}.voice p:last-child{margin:0}.voice h3{font-size:18px;color:var(--acc);margin:1.1em 0 .4em}.voice figure{margin:.6em 0 1em}
.angle{font-size:19px;color:var(--mute)}.figs{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.fig{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}.fig b{display:block;font-size:22px;color:var(--acc)}.fig small{color:var(--mute)}
ul{padding-inline-start:22px}.q{border-inline-start:4px solid var(--acc);padding:4px 14px;font-style:italic}
html[lang=en] body{font-family:Georgia,"Segoe UI",system-ui,serif}.en{direction:ltr;text-align:left;font-family:Georgia,"Segoe UI",system-ui,serif;border-top:1px solid var(--line);margin-top:34px}
.cta{display:inline-block;background:var(--acc);color:var(--bg);text-decoration:none;padding:10px 18px;border-radius:999px;font-weight:700;margin:20px 0}
footer{border-top:1px solid var(--line);color:var(--mute);font-size:14px;padding:18px 0 40px;margin-top:30px}
.list{list-style:none;padding:0}.list li{border-bottom:1px solid var(--line);padding:14px 0}.list a{text-decoration:none;color:var(--ink);font-weight:700;font-size:19px}.list small{display:block;color:var(--mute)}
.sc{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 12px}.sc a{width:40px;height:40px;border-radius:50%;display:grid;place-items:center;background:var(--card);border:1px solid var(--line);color:var(--ink)}.sc svg{width:19px;height:19px;fill:currentColor}"""

def head(title, desc, url, img, extra="", lang="ar", alt=None):
    img = img or BASE + "og.jpg"
    en = lang == "en"
    hl = "".join(f'<link rel="alternate" hreflang="{k}" href="{e(v)}">' for k, v in (alt or {}).items())
    return f"""<!doctype html><html lang="{lang}" dir="{'ltr' if en else 'rtl'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{e(url)}"><meta name="robots" content="index,follow,max-image-preview:large">
<meta name="theme-color" content="#0b1712"><link rel="icon" href="{BASE}favicon.ico" sizes="48x48"><link rel="icon" type="image/png" sizes="96x96" href="{BASE}icon-96.png"><link rel="icon" type="image/png" sizes="192x192" href="{BASE}icon-192.png"><link rel="apple-touch-icon" href="{BASE}icon-180.png">
<meta property="og:site_name" content="{'Shuhud · شهود' if en else 'شهود · Shuhud'}"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{e(url)}"><meta property="og:image" content="{e(img)}">{'<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">' if '/og/' in img else ''}<meta property="og:locale" content="{'en_GB' if en else 'ar_AR'}"><meta property="og:locale:alternate" content="{'ar_AR' if en else 'en_GB'}">{hl}
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{e(img)}">
{extra}<style>{CSS}</style></head><body>
<header class="top"><div class="wrap">{(f'<a class="brand" href="{BASE}?lang=en"><img src="{BASE}icon-192.png" alt="">Shuhud</a><nav><a href="{BASE}en/p/">All pieces</a><a href="{BASE}en/r/">Reserves</a><a href="{BASE}?lang=en#about">About</a></nav>') if en else (f'<a class="brand" href="{BASE}"><img src="{BASE}icon-192.png" alt="">شهود</a><nav><a href="{BASE}p/">كل القطع</a><a href="{BASE}r/">المحميات</a><a href="{BASE}#about">من نحن</a></nav>')}</div></header>
"""

SC = ('<div class="sc">' + "".join(f'<a href="{e(href(x))}" target="_blank" rel="noopener me" title="{e(x.get("name") or x.get("platform"))}" aria-label="{e(x.get("name") or x.get("platform"))}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="{ICONS.get(x.get("platform"), ICONS["web"])}"/></svg></a>' for x in socials) + "</div>") if socials else ""
FOOT_EN = f"""<footer><div class="wrap">{SC}Shuhud · شهود: the world's crises told by the creatures who live them. <a href="{BASE}?lang=en">alshuhud.org</a></div></footer>
</body></html>
"""
FOOT = f"""<footer><div class="wrap">{SC}شهود · Shuhud — أزمات العالم بلسان الكائنات التي تعيشها. <a href="{BASE}">alshuhud.org</a></div></footer>
</body></html>
"""

# light markup in the testimony (same rules as richText() in the page): **bold**, [text](https://…), "## " subheading, "> " quote, ![caption](url)
MD_IMG = re.compile(r"^!\[([^\]\n]*)\]\(((?:https?://|/_blob/|media/)[^\s)]+)\)$")
def md_inline(t):
    t = re.sub(r"\*\*([^*\n]+?)\*\*", r"<strong>\1</strong>", t)
    return re.sub(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)", r'<a href="\2" target="_blank" rel="noopener nofollow">\1</a>', t)
def md_img_src(u):
    if u.startswith("/_blob/"): return BASE + "media/" + re.sub(r"[^\w-]", "", u[7:]) + ".jpg"
    if u.startswith("media/"): return BASE + u
    return u
def rich(src):
    out = []
    for par in re.split(r"\n\s*\n", str(src or "")):
        par = par.strip()
        if not par: continue
        m = MD_IMG.match(par)
        if m:
            out.append(f'<figure><img src="{e(md_img_src(m.group(2)))}" alt="{e(m.group(1))}" loading="lazy">' + (f"<figcaption>{e(m.group(1))}</figcaption>" if m.group(1) else "") + "</figure>")
            continue
        if re.match(r"^##\s+", par):
            out.append(f'<h3>{md_inline(e(re.sub(r"^##\s+", "", par)))}</h3>'); continue
        lines = par.split("\n")
        if all(re.match(r"^>\s?", l) for l in lines):
            out.append('<blockquote class="q">' + "<br>".join(md_inline(e(re.sub(r"^>\s?", "", l))) for l in lines) + "</blockquote>"); continue
        out.append("<p>" + "<br>".join(md_inline(e(l)) for l in lines) + "</p>")
    return "".join(out)
def plain(src):
    t = "\n\n".join(x for x in re.split(r"\n\s*\n", str(src or "")) if not MD_IMG.match(x.strip()))
    t = re.sub(r"(?m)^(##\s+|>\s?)", "", t)
    t = re.sub(r"\*\*([^*\n]+?)\*\*", r"\1", t)
    return re.sub(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)", r"\1", t)

def block(p, ar=True):
    t = (lambda a, b: a if ar else b)
    out = []
    if p.get("angle"): out.append(f'<p class="angle">{e(p["angle"])}</p>')
    if p.get("dispatch"):
        out.append(f'<h2>{t("شهادة " + e(p.get("animalName")), "Testimony of the " + e(p.get("animalName")))}</h2><div class="voice">{rich(p["dispatch"])}</div>')
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

# share images: Facebook, WhatsApp and X read og:image. A ready 1200x630 picture served from alshuhud.org itself
# always shows large (remote Wikipedia photos are often refused or shown small). The narrator sits in a circle when
# the piece has its own event photo. Made once per piece and kept in og/<short>.jpg.
OG_PATH = "data/og-img.json"
try:
    OG = json.load(open(OG_PATH, encoding="utf8"))
except Exception:
    OG = {}
def _fetch(src):
    import urllib.request, time
    if src.startswith(BASE) and os.path.exists(src[len(BASE):]):
        return open(src[len(BASE):], "rb").read()
    if src.startswith("media/") and os.path.exists(src):
        return open(src, "rb").read()
    for k in range(3):
        try:
            req = urllib.request.Request(src, headers={"user-agent": "ShuhudPages/1.0 (https://alshuhud.org)"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read()
        except Exception:
            time.sleep(3 * (k + 1))
    return None
def og_image(sid, src, narr=""):
    key = src + "|" + (narr or "") + ("|fit2" if narr else "")
    path = f"og/{sid}.jpg"
    if not src:
        return ""
    if OG.get(sid) == key and os.path.exists(path):
        return BASE + path
    try:
        from io import BytesIO
        from PIL import Image, ImageOps, ImageDraw
        raw = _fetch(src)
        if not raw:
            return src
        im = ImageOps.fit(Image.open(BytesIO(raw)).convert("RGB"), (1200, 630), Image.LANCZOS, centering=(0.5, 0.42))
        if narr:
            nb = _fetch(narr)
            if nb:
                d = 190
                ni = Image.open(BytesIO(nb)).convert("RGB")
                ar = ni.width / max(1, ni.height)
                # a long or tall creature (a fish, a snake) is shown whole on a parchment ground, not cropped
                if ar > 1.55 or ar < 0.66:
                    inner = int(d * 0.94)
                    c = Image.new("RGB", (d, d), (244, 239, 226))
                    ni.thumbnail((inner, inner), Image.LANCZOS)
                    c.paste(ni, ((d - ni.width) // 2, (d - ni.height) // 2))
                else:
                    c = ImageOps.fit(ni, (d, d), Image.LANCZOS, centering=(0.5, 0.4))
                m = Image.new("L", (d, d), 0); ImageDraw.Draw(m).ellipse((0, 0, d - 1, d - 1), fill=255)
                x, y = 1200 - d - 40, 630 - d - 40
                ImageDraw.Draw(im).ellipse((x - 7, y - 7, x + d + 6, y + d + 6), fill=(244, 239, 226))
                im.paste(c, (x, y), m)
        os.makedirs("og", exist_ok=True)
        im.save(path, "JPEG", quality=84, optimize=True, progressive=True)
        OG[sid] = key
        return BASE + path
    except Exception:
        return src

SHORT_PATH = "data/short-ids.json"
SHORT = json.load(open(SHORT_PATH, encoding="utf8")) if os.path.exists(SHORT_PATH) else {}
if not isinstance(SHORT, dict): SHORT = {}
def short_id(pid):
    if pid in SHORT: return SHORT[pid]
    taken = set(SHORT.values()) | {"index"} | set(pieces)
    m = re.match(r"^env-\d{8}-(?:custom-)?(.+)$", pid)
    toks = m.group(1).split("-") if m else [pid[:8]]
    cand = [ "-".join(toks[:n]) for n in range(2 if len(toks) > 1 else 1, len(toks) + 1)]
    cand += [cand[-1] + "-" + str(k) for k in range(2, 99)]
    for c in cand:
        if c not in taken and SAFE.match(c):
            SHORT[pid] = c
            return c
    SHORT[pid] = pid
    return pid

# a person who opens a piece page is taken to the same piece inside the site itself (same look, photos, sound);
# search engines and link previews read this page as it is
def go_script(pid, lang="ar"):
    return ('<script>if(!/bot|crawl|spider|slurp|facebookexternalhit|whatsapp|telegram|twitter|discord|linkedin|skype|preview|lighthouse|headless/i.test(navigator.userAgent)){'
            'document.documentElement.style.background="#0b1712";document.write("<style>body{visibility:hidden}</style>");'
            f'location.replace("/?p={pid}{"&lang=en" if lang == "en" else ""}"+location.hash)}}</script>\n')

os.makedirs("p", exist_ok=True)
built = set()
en_files = set()
files = set()
items = sorted(pieces.values(), key=lambda p: (date_of(p), str(p.get("createdAt") or "")), reverse=True)
for p in items:
    pid = p["id"]
    if not SAFE.match(pid):
        continue
    sid = short_id(pid)
    url = f"{BASE}p/{sid}"
    d = date_of(p)
    img, credit = image_of(p)
    en = p.get("en") if isinstance(p.get("en"), dict) else {}
    title = f'{p["headline"]} | شهود'
    desc = short(p.get("angle") or p.get("fact") or plain(p.get("dispatch")))
    ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": short(p["headline"], 110),
          "description": desc, "inLanguage": ["ar", "en"] if en else "ar", "mainEntityOfPage": url,
          "author": {"@type": "Person", "name": "Kamal Al-Salami", "alternateName": "كمال السلامي"},
          "publisher": {"@type": "NewsMediaOrganization", "name": "شهود", "alternateName": "Shuhud", "url": BASE, "logo": {"@type": "ImageObject", "url": BASE + "icon-512.png"}}}
    if d: ld["datePublished"] = str(p.get("createdAt") or d)[:25]
    if img: ld["image"] = [img]
    if en.get("headline"): ld["alternativeHeadline"] = short(en["headline"], 110)
    url_en = f"{BASE}en/p/{sid}"
    alt = {"ar": url, "en": url_en, "x-default": url} if en.get("headline") else None
    extra = go_script(pid) + '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
    kick = " · ".join(x for x in (e(p.get("category")), e(p.get("place"))) if x)
    share = og_image(sid, img, narr_of(p) if str(p.get("imageUrl") or "") else "")
    body = [head(title, desc, url, share or img, extra, "ar", alt), '<main class="wrap"><article>']
    body.append(f'<div class="kick">{p.get("animalEmoji","")} {e(p.get("animalName"))}{" · " + kick if kick else ""}</div>')
    body.append(f'<h1>{e(p["headline"])}</h1><div class="meta">{nice(d) if d else ""}{" · " if d else ""}{e(p.get("crisis"))}</div>')
    if img:
        nr = narr_of(p)
        nr = f'<img class="narr" src="{e(nr)}" alt="{e(p.get("animalName"))}">' if nr and nr != img else ""
        body.append(f'<figure><img src="{e(img)}" alt="{e(p.get("crisis") or p.get("animalName"))}" loading="eager">{nr}{f"<figcaption>{e(credit)}</figcaption>" if credit else ""}</figure>')
    body.append(block(p, True))
    if en.get("headline"):
        en_full = {**en, "figures": en.get("figures") or [], "sources": en.get("sources") or p.get("sources")}
        body.append(f'<section class="en" lang="en" dir="ltr"><h1>{e(en["headline"])}</h1><div class="meta">{nice(d, False) if d else ""}{" · " if d else ""}{e(en.get("crisis"))}</div>{block(en_full, False)}</section>')
    body.append(f'<a class="cta" href="{BASE}">اقرأ المزيد في شهود ←</a></article></main>')
    body.append(FOOT)
    # the short address is the page; the old long address stays for links already shared
    for name in {sid, pid}:
        with open(f"p/{name}.html", "w", encoding="utf8") as fh:
            fh.write("\n".join(body))
        files.add(name)
    built.add(pid)
    # English page (17 Nov 2026, Kamal): its own address, title, description and language, linked to the Arabic one
    if en.get("headline"):
        en_full = {**en, "figures": en.get("figures") or [], "sources": en.get("sources") or p.get("sources")}
        t_en = f'{en["headline"]} | Shuhud'
        d_en = short(en.get("angle") or en.get("fact") or plain(en.get("dispatch"))) or desc
        ld_en = {**ld, "headline": short(en["headline"], 110), "description": d_en, "inLanguage": "en", "mainEntityOfPage": url_en,
                 "publisher": {**ld["publisher"], "name": "Shuhud", "alternateName": "شهود"}}
        ld_en.pop("alternativeHeadline", None)
        x_en = go_script(pid, "en") + '<script type="application/ld+json">' + json.dumps(ld_en, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
        kick_en = " · ".join(x for x in (e(en.get("category") or ""), e(en.get("place"))) if x)
        b = [head(t_en, d_en, url_en, share or img, x_en, "en", alt), '<main class="wrap"><article lang="en" dir="ltr" style="text-align:left">']
        b.append(f'<div class="kick">{p.get("animalEmoji","")} {e(en.get("animalName") or p.get("animalName"))}{" · " + kick_en if kick_en else ""}</div>')
        b.append(f'<h1>{e(en["headline"])}</h1><div class="meta">{nice(d, False) if d else ""}{" · " if d else ""}{e(en.get("crisis"))}</div>')
        if img:
            nr = narr_of(p)
            nr = f'<img class="narr" src="{e(nr)}" alt="{e(en.get("animalName") or p.get("animalName"))}">' if nr and nr != img else ""
            b.append(f'<figure><img src="{e(img)}" alt="{e(en.get("crisis") or en.get("animalName") or "")}" loading="eager">{nr}{f"<figcaption>{e(en.get('imageCredit') or credit.replace('صورة أرشيفية', 'Archive photo'))}</figcaption>" if credit else ""}</figure>')
        b.append(block(en_full, False))
        b.append(f'<p class="meta"><a href="{url}" lang="ar">اقرأ بالعربية ←</a></p>')
        b.append(f'<a class="cta" href="{BASE}?lang=en">More on Shuhud →</a></article></main>')
        b.append(FOOT_EN)
        os.makedirs("en/p", exist_ok=True)
        with open(f"en/p/{sid}.html", "w", encoding="utf8") as fh:
            fh.write("\n".join(b))
        en_files.add(sid)

# pages of pieces that were deleted are removed
for f in glob.glob("p/*.html"):
    n = os.path.basename(f)[:-5]
    if n != "index" and n not in files:
        os.remove(f)

for f in glob.glob("en/p/*.html"):
    n = os.path.basename(f)[:-5]
    if n != "index" and n not in en_files:
        os.remove(f)

# archive
rows = []
for p in items:
    if p["id"] not in built: continue
    d = date_of(p)
    rows.append(f'<li><a href="{SHORT[p["id"]]}">{e(p["headline"])}</a><small>{p.get("animalEmoji","")} {e(p.get("animalName"))} · {nice(d) if d else ""}</small></li>')
arch = head("كل القطع | شهود — أزمات العالم بلسان الكائنات التي تعيشها",
            "أرشيف قطع شهود: أزمات العالم من زاويتها البيئية بلسان الكائنات التي تعيشها، بالعربية والإنجليزية.", BASE + "p/", "", "", "ar", {"ar": BASE + "p/", "en": BASE + "en/p/", "x-default": BASE + "p/"})
with open("p/index.html", "w", encoding="utf8") as fh:
    fh.write(arch + f'<main class="wrap"><article><h1>كل القطع</h1><div class="meta">{len(rows)} قطعة</div><ul class="list">' + "\n".join(rows) + "</ul></article></main>" + FOOT)

# reserves: one page per reserve (r/<name>.html) from data/reserves.json (written by build.py from the page's RESERVES list)
RS_SLUG = {"ahwar": "iraq-marshes", "wadirum": "wadi-rum", "rasmohammed": "ras-mohammed", "samhan": "jabal-samhan"}
reserves = [r for r in load("data/reserves.json") if isinstance(r, dict) and re.match(r"^[a-z]{2,24}$", str(r.get("id") or "")) and isinstance(r.get("ar"), dict)]
# Kamal's edits from the Claude copy (synced into data/reserves-db.json) are laid over the page's text
for d in load("data/reserves-db.json"):
    for r in reserves:
        if isinstance(d, dict) and d.get("id") == r["id"]:
            r["ar"] = {**r.get("ar", {}), **(d.get("ar") or {})}
            r["en"] = {**(r.get("en") or {}), **(d.get("en") or {})}
            if isinstance(d.get("src"), list): r["src"] = d["src"]
            if d.get("img"): r["img"], r["credit"] = d["img"], d.get("credit") or ""
def rs_slug(r): return RS_SLUG.get(r["id"], r["id"])
def rs_norm(t): return re.sub(r"[ً-ْـ]", "", str(t or "")).lower()
def rs_pieces(r):
    keys = [rs_norm(k) for k in (r.get("match") or []) if k]
    out = []
    for p in items:
        if p["id"] not in built: continue
        en = p.get("en") if isinstance(p.get("en"), dict) else {}
        t = rs_norm(" ".join(str(x or "") for x in (p.get("place"), p.get("headline"), p.get("angle"), p.get("dispatch"), en.get("place"))))
        if any(k in t for k in keys): out.append(p)
    return out
def rs_block(x, ar, r, ps):
    t = (lambda a, b: a if ar else b)
    o = [f'<div class="angle">{rich(x.get("about"))}</div>']
    if x.get("more"): o.append(f'<div class="voice">{rich(x["more"])}</div>')
    figs = [f for f in (x.get("figs") or []) if isinstance(f, list) and len(f) >= 2]
    if figs:
        o.append('<div class="figs">' + "".join(f'<div class="fig"><b>{e(v)}</b><small>{e(l)}</small></div>' for v, l, *_ in figs) + "</div>")
    sp = [s[0] for s in (x.get("sp") or []) if s]
    if sp: o.append(f'<h2>{t("أبرز الكائنات","Notable creatures")}</h2><ul>' + "".join(f"<li>{e(n)}</li>" for n in sp) + "</ul>")
    if x.get("pl"): o.append(f'<h2>{t("أبرز النباتات","Notable plants")}</h2><ul>' + "".join(f"<li>{e(n)}</li>" for n in x["pl"]) + "</ul>")
    if x.get("th"): o.append(f'<h2>{t("ما يهددها","Threats")}</h2><p>{e(x["th"])}</p>')
    if ps:
        o.append(f'<h2>{t("شهادات من هنا","Testimonies from here")}</h2><ul>' + "".join(
            f'<li><a href="{BASE}p/{SHORT[p["id"]]}">{e(p["headline"] if ar else ((p.get("en") or {}).get("headline") or p["headline"]))}</a></li>' for p in ps) + "</ul>")
    ll = r.get("ll") or []
    if len(ll) == 2:
        o.append(f'<p><a href="https://www.openstreetmap.org/?mlat={ll[0]}&amp;mlon={ll[1]}#map=8/{ll[0]}/{ll[1]}" target="_blank" rel="noopener">{t("🗺️ على الخريطة","🗺️ On the map")} ↗</a></p>')
    return "\n".join(o)
os.makedirs("r", exist_ok=True)
rs_files = set()
rs_en_files = set()
rs_rows_en = []
rs_rows = []
for r in reserves:
    ar, en = r["ar"], (r.get("en") if isinstance(r.get("en"), dict) else {})
    slug = rs_slug(r)
    url = f"{BASE}r/{slug}"
    img = str(r.get("img") or "")
    title = f'{ar.get("name")}{" | " + en["name"] if en.get("name") else ""} — محمية في {ar.get("cty")} | شهود'
    desc = short(plain(ar.get("about")))
    share = og_image("r-" + slug, img) if img.startswith("http") else ""
    ps = rs_pieces(r)
    ld = {"@context": "https://schema.org", "@type": "Place", "name": ar.get("name"), "alternateName": en.get("name"),
          "description": desc, "url": url, "containedInPlace": {"@type": "Country", "name": en.get("cty") or ar.get("cty")}}
    ll = r.get("ll") or []
    if len(ll) == 2: ld["geo"] = {"@type": "GeoCoordinates", "latitude": ll[0], "longitude": ll[1]}
    if img: ld["image"] = [share or img]
    goto = ('<script>if(!/bot|crawl|spider|slurp|facebookexternalhit|whatsapp|telegram|twitter|discord|linkedin|skype|preview|lighthouse|headless/i.test(navigator.userAgent)){'
            'document.documentElement.style.background="#0b1712";document.write("<style>body{visibility:hidden}</style>");'
            f'location.replace("/?r={r["id"]}")}}</script>\n')
    extra = goto + '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
    url_en = f"{BASE}en/r/{slug}"
    alt = {"ar": url, "en": url_en, "x-default": url} if en.get("name") else None
    body = [head(title, desc, url, share or img, extra, "ar", alt), '<main class="wrap"><article>']
    body.append(f'<div class="kick"><svg width="18" height="18" style="vertical-align:-3px" aria-hidden="true" viewBox="0 0 24 24"><path d="M2.6 10.2L10.6 16.6h2.8l8-6.4z" fill="#a4855a"/><path d="M12 16.4L3.6 10.4M12 16.4L6.4 10.4M12 16.4L9.2 10.4M12 16.4V10.4M12 16.4l2.8-6M12 16.4l5.6-6M12 16.4l8.4-6" stroke="#6e5333" stroke-width=".9" stroke-linecap="round"/><path d="M.7 10.6C1.4 2.6 22.6 2.6 23.3 10.6C21.6 11.4 2.4 11.4.7 10.6Z" fill="#7cbf4e"/><path d="M2.6 8.2C6 5.6 18 5.6 21.4 8.2" stroke="#a8dc6f" stroke-width=".7" fill="none" stroke-linecap="round" opacity=".8"/><path d="M10.7 16.2h2.6l.4 6.4h-3.4z" fill="#7a5a36"/><path d="M8.8 22.8h6.4" stroke="#7a5a36" stroke-width="1.2" stroke-linecap="round"/></svg> {r.get("cc","")} {e(ar.get("cty"))} · المحميات</div><h1>{e(ar.get("name"))}</h1><div class="meta">{e(ar.get("st"))}</div>')
    if img:
        body.append(f'<figure><img src="{e(img)}" alt="{e(ar.get("name"))}" loading="eager">{f"<figcaption>{e(r.get("credit"))}</figcaption>" if r.get("credit") else ""}</figure>')
    body.append(rs_block(ar, True, r, ps))
    if en.get("name"):
        body.append(f'<section class="en" lang="en" dir="ltr"><h1>{e(en["name"])}</h1><div class="meta">{e(en.get("cty"))} · {e(en.get("st"))}</div>{rs_block(en, False, r, ps)}</section>')
    srcs = [x for x in (r.get("src") or []) if isinstance(x, list) and len(x) >= 2 and str(x[1]).startswith("http")]
    if srcs:
        body.append('<h2>المصادر · Sources</h2><ul>' + "".join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(n)}</a></li>' for n, u, *_ in srcs) + "</ul>")
    body.append(f'<a class="cta" href="{BASE}?r={r["id"]}">كل المحميات في شهود ←</a></article></main>')
    body.append(FOOT)
    with open(f"r/{slug}.html", "w", encoding="utf8") as fh:
        fh.write("\n".join(body))
    rs_files.add(slug)
    if en.get("name"):
        t_en = f'{en["name"]}, a nature reserve in {en.get("cty")} | Shuhud'
        d_en = short(plain(en.get("about"))) or desc
        ld_en = {**ld, "name": en["name"], "alternateName": ar.get("name"), "description": d_en, "url": url_en}
        go_en = goto.replace(f'/?r={r["id"]}', f'/?r={r["id"]}&lang=en')
        x_en = go_en + '<script type="application/ld+json">' + json.dumps(ld_en, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
        b = [head(t_en, d_en, url_en, share or img, x_en, "en", alt), '<main class="wrap"><article lang="en" dir="ltr" style="text-align:left">']
        b.append(f'<div class="kick"><svg width="18" height="18" style="vertical-align:-3px" aria-hidden="true" viewBox="0 0 24 24"><path d="M2.6 10.2L10.6 16.6h2.8l8-6.4z" fill="#a4855a"/><path d="M12 16.4L3.6 10.4M12 16.4L6.4 10.4M12 16.4L9.2 10.4M12 16.4V10.4M12 16.4l2.8-6M12 16.4l5.6-6M12 16.4l8.4-6" stroke="#6e5333" stroke-width=".9" stroke-linecap="round"/><path d="M.7 10.6C1.4 2.6 22.6 2.6 23.3 10.6C21.6 11.4 2.4 11.4.7 10.6Z" fill="#7cbf4e"/><path d="M2.6 8.2C6 5.6 18 5.6 21.4 8.2" stroke="#a8dc6f" stroke-width=".7" fill="none" stroke-linecap="round" opacity=".8"/><path d="M10.7 16.2h2.6l.4 6.4h-3.4z" fill="#7a5a36"/><path d="M8.8 22.8h6.4" stroke="#7a5a36" stroke-width="1.2" stroke-linecap="round"/></svg> {r.get("cc","")} {e(en.get("cty"))} · Reserves</div><h1>{e(en["name"])}</h1><div class="meta">{e(en.get("st"))}</div>')
        if img:
            b.append(f'<figure><img src="{e(img)}" alt="{e(en["name"])}" loading="eager">{f"<figcaption>{e(r.get("credit"))}</figcaption>" if r.get("credit") else ""}</figure>')
        b.append(rs_block(en, False, r, ps).replace(f'{BASE}p/', f'{BASE}en/p/'))
        if srcs:
            b.append('<h2>Sources</h2><ul>' + "".join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(n)}</a></li>' for n, u, *_ in srcs) + "</ul>")
        b.append(f'<p class="meta"><a href="{url}" lang="ar">اقرأ بالعربية ←</a></p>')
        b.append(f'<a class="cta" href="{BASE}?r={r["id"]}&amp;lang=en">All reserves on Shuhud →</a></article></main>')
        b.append(FOOT_EN)
        os.makedirs("en/r", exist_ok=True)
        with open(f"en/r/{slug}.html", "w", encoding="utf8") as fh:
            fh.write("\n".join(b))
        rs_en_files.add(slug)
        rs_rows_en.append(f'<li><a href="{slug}">{e(en["name"])}</a><small>{r.get("cc","")} {e(en.get("cty"))} · {e(en.get("st"))}</small></li>')
    rs_rows.append(f'<li><a href="{slug}">{e(ar.get("name"))}</a><small>{r.get("cc","")} {e(ar.get("cty"))} · {e(ar.get("st"))}</small></li>')
for f in glob.glob("en/r/*.html"):
    n = os.path.basename(f)[:-5]
    if n != "index" and n not in rs_en_files:
        os.remove(f)
if rs_rows_en:
    rh_en = head("Nature reserves | Shuhud: a selection of the Arab world's and the world's great reserves",
                 "Selected nature reserves in the Arab world and beyond: their creatures, plants and threats, with testimonies from there, in English and Arabic.",
                 BASE + "en/r/", "", "", "en", {"ar": BASE + "r/", "en": BASE + "en/r/", "x-default": BASE + "r/"})
    with open("en/r/index.html", "w", encoding="utf8") as fh:
        fh.write(rh_en + f'<main class="wrap"><article lang="en" dir="ltr" style="text-align:left"><h1>Nature reserves</h1><div class="meta">{len(rs_rows_en)} reserves</div><ul class="list">' + "\n".join(rs_rows_en) + "</ul></article></main>" + FOOT_EN)
for f in glob.glob("r/*.html"):
    n = os.path.basename(f)[:-5]
    if n != "index" and n not in rs_files:
        os.remove(f)
if reserves:
    rh = head("المحميات | شهود — مختارات من أهم المحميات الطبيعية في العالم العربي والعالم",
              "محميات طبيعية مختارة من العالم العربي والعالم: كائناتها ونباتاتها وما يهددها، وشهادات من هناك، بالعربية والإنجليزية.", BASE + "r/", "", "", "ar", {"ar": BASE + "r/", "en": BASE + "en/r/", "x-default": BASE + "r/"})
    with open("r/index.html", "w", encoding="utf8") as fh:
        fh.write(rh + f'<main class="wrap"><article><h1>المحميات</h1><div class="meta">{len(rs_rows)} محمية · Nature reserves</div><ul class="list">' + "\n".join(rs_rows) + "</ul></article></main>" + FOOT)

# English archive
if en_files:
    rows_en = []
    for p in items:
        if p["id"] not in built or SHORT[p["id"]] not in en_files: continue
        en = p.get("en") or {}
        d = date_of(p)
        rows_en.append(f'<li><a href="{SHORT[p["id"]]}">{e(en["headline"])}</a><small>{p.get("animalEmoji","")} {e(en.get("animalName") or "")} · {nice(d, False) if d else ""}</small></li>')
    arch_en = head("All pieces | Shuhud: the world's crises told by the creatures who live them",
                   "The Shuhud archive: the world's crises seen through their environmental impact, told in the first person by the creatures who live them, in English and Arabic.",
                   BASE + "en/p/", "", "", "en", {"ar": BASE + "p/", "en": BASE + "en/p/", "x-default": BASE + "p/"})
    with open("en/p/index.html", "w", encoding="utf8") as fh:
        fh.write(arch_en + f'<main class="wrap"><article lang="en" dir="ltr" style="text-align:left"><h1>All pieces</h1><div class="meta">{len(rows_en)} pieces</div><ul class="list">' + "\n".join(rows_en) + "</ul></article></main>" + FOOT_EN)

# sitemap
today = datetime.date.today().isoformat()
urls = [f"  <url><loc>{BASE}</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>",
        f"  <url><loc>{BASE}p/</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>0.8</priority></url>"]
for p in items:
    if p["id"] in built:
        d = date_of(p) or today
        urls.append(f"  <url><loc>{BASE}p/{SHORT[p['id']]}</loc><lastmod>{d}</lastmod><priority>0.7</priority></url>")
        if SHORT[p["id"]] in en_files:
            urls.append(f"  <url><loc>{BASE}en/p/{SHORT[p['id']]}</loc><lastmod>{d}</lastmod><priority>0.7</priority></url>")
if en_files:
    urls.append(f"  <url><loc>{BASE}en/p/</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>0.7</priority></url>")
if reserves:
    urls.append(f"  <url><loc>{BASE}r/</loc><lastmod>{today}</lastmod><priority>0.7</priority></url>")
    for r in reserves:
        urls.append(f"  <url><loc>{BASE}r/{rs_slug(r)}</loc><lastmod>{today}</lastmod><priority>0.7</priority></url>")
        if rs_slug(r) in rs_en_files:
            urls.append(f"  <url><loc>{BASE}en/r/{rs_slug(r)}</loc><lastmod>{today}</lastmod><priority>0.7</priority></url>")
    if rs_en_files:
        urls.append(f"  <url><loc>{BASE}en/r/</loc><lastmod>{today}</lastmod><priority>0.7</priority></url>")
with open("sitemap.xml", "w", encoding="utf8") as fh:
    fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n")
print(len(built), "piece pages,", len(en_files), "English,", len(reserves), "reserve pages,", len(rs_en_files), "English")
with open(SHORT_PATH, "w", encoding="utf8") as fh:
    json.dump(SHORT, fh, ensure_ascii=False, indent=0)
with open(OG_PATH, "w", encoding="utf8") as fh:
    json.dump(OG, fh, ensure_ascii=False, indent=0)
with open(WIKI_PATH, "w", encoding="utf8") as fh:
    json.dump(WIKI, fh, ensure_ascii=False, indent=0)
