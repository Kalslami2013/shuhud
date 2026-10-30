# Builds index.html for the standalone app from the shared page source (shuhud.html).
import re,sys
src=open(sys.argv[1],encoding='utf8').read()
src=re.sub(r'<link rel="apple-touch-icon"[^>]*>\n?','',src); src=re.sub(r'<link rel="icon"[^>]*>\n?','',src)
head='''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="الشهود"><meta name="theme-color" content="#0b1712">
<link rel="manifest" href="manifest.webmanifest"><link rel="apple-touch-icon" href="icon-180.png"><link rel="icon" href="icon-192.png">
<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>
</head><body>
'''
src=src.replace('\n<script>\n','\n<script src="local.js"></script>\n<script>\n',1)
open(sys.argv[2],'w',encoding='utf8').write(head+src+'\n</body></html>\n')
