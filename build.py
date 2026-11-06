# Builds index.html for the standalone app from the shared page source (shuhud.html).
import re,sys,time
src=open(sys.argv[1],encoding='utf8').read()
src=re.sub(r'<link rel="apple-touch-icon"[^>]*>\n?','',src); src=re.sub(r'<link rel="icon"[^>]*>\n?','',src)
head='''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="الشهود"><meta name="theme-color" content="#0b1712">
<link rel="manifest" href="manifest.webmanifest"><link rel="apple-touch-icon" href="icon-180.png"><link rel="icon" href="icon-192.png">
<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>
</head><body>
'''
BUILD=str(int(time.time()))
open('version.txt','w').write(BUILD)
src=src.replace('\n<script>\n','\n<script>window.SHUHUD_BUILD="'+BUILD+'"</script>\n<script src="local.js?v='+BUILD+'"></script>\n<script>\n',1)
open(sys.argv[2],'w',encoding='utf8').write(head.replace('</head>','<meta name="robots" content="noindex,nofollow"><link rel="canonical" href="https://kalslami2013.github.io/shuhud/reader.html">\n</head>')+src+'\n</body></html>\n')
# reader page: the same page with no newsroom and no controls, for the public
BASE="https://kalslami2013.github.io/shuhud/"
DESC_AR="الشهود: منصة صحفية بالعربية والإنجليزية تروي أزمات العالم من زاويتها البيئية بلسان الكائنات التي تعيشها، من الحروب والتلوث إلى الجفاف والزلازل، مع الأرقام ومصادرها."
DESC_EN="Al-Shuhud (The Witnesses): an Arabic-English journalism platform telling the world's crises from their environmental side, in the voices of the species living them."
seo=f'''<title>الشهود | أزمات العالم بلسان الكائنات التي تعيشها — Al-Shuhud</title>
<meta name="description" content="{DESC_AR}"><link rel="canonical" href="{BASE}reader.html"><meta name="robots" content="index,follow">
<meta property="og:type" content="website"><meta property="og:site_name" content="الشهود · Al-Shuhud"><meta property="og:title" content="الشهود — أزمات العالم بلسان الكائنات التي تعيشها"><meta property="og:description" content="{DESC_AR}"><meta property="og:url" content="{BASE}reader.html"><meta property="og:image" content="{BASE}og.jpg"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:locale" content="ar_AR"><meta property="og:locale:alternate" content="en_GB">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="الشهود · Al-Shuhud"><meta name="twitter:description" content="{DESC_EN}"><meta name="twitter:image" content="{BASE}og.jpg">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"NewsMediaOrganization","name":"الشهود","alternateName":"Al-Shuhud","url":"{BASE}reader.html","logo":"{BASE}icon-512.png","description":"{DESC_EN}","founder":{{"@type":"Person","name":"Kamal Al-Salami","alternateName":"كمال السلامي","jobTitle":"Founder and editor-in-chief"}},"inLanguage":["ar","en"]}}</script>
'''
rhead=head.replace('href="manifest.webmanifest"','href="reader.webmanifest"').replace('</head>',seo+'</head>')
rsrc=src.replace('<script>window.SHUHUD_BUILD=','<script>window.SHUHUD_READER=true;window.SHUHUD_BUILD=',1).replace('<title>الشهود</title>','',1)
open('reader.html','w',encoding='utf8').write(rhead+rsrc+'\n</body></html>\n')
