# Builds newsroom.html (Kamal's standalone app, pass it as argv[2]) and the public index.html/reader.html from the shared page source (shuhud.html).
import re,sys,time,json
src=open(sys.argv[1],encoding='utf8').read()
src=re.sub(r'<link rel="apple-touch-icon"[^>]*>\n?','',src); src=re.sub(r'<link rel="icon"[^>]*>\n?','',src)
head='''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="شهود"><meta name="theme-color" content="#0b1712">
<link rel="manifest" href="manifest.webmanifest"><link rel="apple-touch-icon" href="icon-180.png"><link rel="icon" href="/favicon.ico" sizes="48x48"><link rel="icon" type="image/png" sizes="96x96" href="/icon-96.png"><link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">
<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>
</head><body>
'''
BUILD=str(int(time.time()))
open('version.txt','w').write(BUILD)
src=src.replace('\n<script>\n','\n<script>window.SHUHUD_BUILD="'+BUILD+'"</script>\n<script src="local.js?v='+BUILD+'"></script>\n<script>\n',1)
open(sys.argv[2],'w',encoding='utf8').write(head.replace('</head>','<meta name="robots" content="noindex,nofollow"><link rel="canonical" href="https://alshuhud.org/">\n<meta property="og:type" content="website"><meta property="og:site_name" content="شهود · Shuhud"><meta property="og:title" content="شهود — أزمات العالم بلسان الكائنات التي تعيشها"><meta property="og:url" content="https://alshuhud.org/"><meta property="og:image" content="https://alshuhud.org/og.jpg"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="https://alshuhud.org/og.jpg">\n</head>')+src+'\n</body></html>\n')
# reader page: the same page with no newsroom and no controls, for the public
BASE="https://alshuhud.org/"
DESC_AR="شهود: منصة صحفية بالعربية والإنجليزية تروي أزمات العالم من زاويتها البيئية بلسان الكائنات التي تعيشها، من الحروب والتلوث إلى الجفاف والزلازل، مع الأرقام ومصادرها."
DESC_EN="Shuhud (The Witnesses): an Arabic-English journalism platform telling the world's crises from their environmental side, in the voices of the species living them."
seo=f'''<title>شهود | أزمات العالم بلسان الكائنات التي تعيشها — Shuhud</title>
<meta name="description" content="{DESC_AR}"><link rel="canonical" href="{BASE}"><meta name="robots" content="index,follow">
<meta property="og:type" content="website"><meta property="og:site_name" content="شهود · Shuhud"><meta property="og:title" content="شهود — أزمات العالم بلسان الكائنات التي تعيشها"><meta property="og:description" content="{DESC_AR}"><meta property="og:url" content="{BASE}"><meta property="og:image" content="{BASE}og.jpg"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:locale" content="ar_AR"><meta property="og:locale:alternate" content="en_GB">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="شهود · Shuhud"><meta name="twitter:description" content="{DESC_EN}"><meta name="twitter:image" content="{BASE}og.jpg">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"NewsMediaOrganization","name":"شهود","alternateName":"Shuhud","url":"{BASE}","logo":"{BASE}icon-512.png","description":"{DESC_EN}","inLanguage":["ar","en"]}}</script>
'''
# Cloudflare Web Analytics (free, no cookies): public pages only, not newsroom.html
CFWA='<!-- Cloudflare Web Analytics --><script type=\'module\' src=\'https://static.cloudflareinsights.com/beacon.min.js\' data-cf-beacon=\'{"token": "729a651c282448f48d9b144cfcefabd8"}\'></script><!-- End Cloudflare Web Analytics -->\n'
rhead=head.replace('href="manifest.webmanifest"','href="reader.webmanifest"').replace('</head>',seo+CFWA+'</head>')
rsrc=src.replace('<script>window.SHUHUD_BUILD=','<script>window.SHUHUD_READER=true;window.SHUHUD_BUILD=',1).replace('<title>شهود</title>','',1)
# the public page carries none of the newsroom's tools: their markup is cut out, and lookups of the removed elements get a harmless stand-in
CUT_IDS = set()
def cut(html, tag, attr):
    i = html.find(attr)
    if i < 0: return html
    a = html.rfind('<'+tag, 0, i)
    depth, j = 0, a
    rx = re.compile(r'<(/?)'+tag+r'\b[^>]*>')
    for m in rx.finditer(html, a):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            CUT_IDS.update(re.findall(r'\bid="([\w-]+)"', html[a:m.end()]))
            return html[:a] + html[m.end():]
    return html
for tag, attr in (('section','id="v-track"'),('section','id="v-desk"'),('div','id="gh-box"'),('div','id="media-add"'),('div','id="s-form"'),('div','id="p-form"'),('div','id="studio"'),
                  ('button','id="media-add-btn"'),('button','id="gh-link"'),('button','id="gh-unlink"'),('button','id="s-add-btn"'),('button','id="p-add-btn"'),
                  ('div','id="run-live"'),('section','id="v-guide"'),('button','role="tab" data-view="guide"'),('button','role="tab" data-view="track"'),('button','role="tab" data-view="desk"')):
    rsrc = cut(rsrc, tag, attr)
NIL = 'const __nil=new Proxy(function(){},{get:(t,k)=>k===Symbol.iterator?()=>[][Symbol.iterator]():k===Symbol.toPrimitive?()=>"":k==="then"?undefined:k==="length"?0:(k==="hidden"||k==="disabled")?true:["value","textContent","innerHTML","innerText","src","href","className"].includes(k)?"":["files","options","children"].includes(k)?[]:__nil,set:()=>true,apply:()=>__nil});\nconst __CUT=new Set(%s);\nconst $=s=>{const e=document.querySelector(s);if(e)return e;const m=/^#([\\w-]+)/.exec(s);return m&&__CUT.has(m[1])?__nil:null};'
assert rsrc.count('const $=s=>document.querySelector(s);')==1
rsrc = rsrc.replace('const $=s=>document.querySelector(s);', NIL.replace('%s', json.dumps(sorted(CUT_IDS))), 1)
# and the wording of the newsroom-only labels (API key, GitHub token, studio, desk) is blanked in its translations
rsrc = re.sub(r'\b((?:key|gh|st|desk|nav(?:Desk|Track|Guide)|run)[A-Z]\w*|keyLbl|ghLbl):"(?:[^"\\]|\\.)*"', r'\1:""', rsrc)
# the public page is the site's front page (alshuhud.org/); reader.html stays for old links
for f in ('index.html','reader.html'):open(f,'w',encoding='utf8').write(rhead+rsrc+'\n</body></html>\n')

# reserves: the RESERVES list of the page is saved as data/reserves.json, from which scripts/pages.py
# builds one page per reserve (r/<name>.html) for search engines
import subprocess
_m=re.search(r'const RESERVES=(\[.*?\n\]);',src,re.S)
if _m:
  try:
    _j=subprocess.run(['node','-e','process.stdout.write(JSON.stringify(eval(require("fs").readFileSync(0,"utf8"))))'],input=_m.group(1),capture_output=True,text=True,timeout=30).stdout
    _d=json.loads(_j) if _j else None
    if isinstance(_d,list) and _d:
      _ord=re.search(r'const RS_ORDER=(\[[^\]]*\])',src)
      _o=json.loads(_ord.group(1)) if _ord else []
      _d.sort(key=lambda r:_o.index(r['id']) if r['id'] in _o else 99)
      open('data/reserves.json','w',encoding='utf8').write(json.dumps(_d,ensure_ascii=False,indent=1))
  except Exception as _e: print('reserves.json not written:',_e)

# extinctions: EXT_MASS / EXT_HUMAN / EXT_SIXTH of the page are saved as data/extinct.json for scripts/pages.py (x/ and en/x/)
try:
  _mm={}
  for _k in ("EXT_MASS","EXT_HUMAN","EXT_SIXTH"):
    _m=re.search(r'const '+_k+r'=(.*?);\n',src,re.S)
    if _m:_mm[_k]=json.loads(_m.group(1))
  if len(_mm)==3:open('data/extinct.json','w',encoding='utf8').write(json.dumps(_mm,ensure_ascii=False,indent=1))
except Exception as _e: print('extinct.json not written:',_e)
