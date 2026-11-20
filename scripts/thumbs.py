"""Light previews for the Media gallery (20 Nov 2026): every image in media/ gets media/t/<name>.webp
(at most 960 px wide, quality 78). Originals stay untouched for downloads and the lightbox.
Writes data/thumbs.json (list of names that have a preview). Free GitHub job, no Claude."""
import os,json
from PIL import Image
SRC="media";DST="media/t";os.makedirs(DST,exist_ok=True)
done=[]
for n in sorted(os.listdir(SRC)):
    p=os.path.join(SRC,n)
    if not os.path.isfile(p) or not n.lower().endswith((".png",".jpg",".jpeg",".webp")):continue
    base=os.path.splitext(n)[0];out=os.path.join(DST,base+".webp")
    try:
        if not os.path.exists(out) or os.path.getmtime(out)<os.path.getmtime(p):
            im=Image.open(p);im=im.convert("RGBA") if im.mode in("P","LA") else im
            if im.mode=="RGBA":bg=Image.new("RGB",im.size,(7,18,13));bg.paste(im,mask=im.split()[3]);im=bg
            else:im=im.convert("RGB")
            if im.width>960:im=im.resize((960,round(im.height*960/im.width)),Image.LANCZOS)
            im.save(out,"WEBP",quality=78,method=5)
        done.append(n)
    except Exception as e:print("skip",n,e)
import subprocess,shutil
if shutil.which("ffmpeg"):
    for n in sorted(os.listdir(SRC)):
        if not n.lower().endswith((".mp4",".webm")):continue
        p=os.path.join(SRC,n);out=os.path.join(DST,os.path.splitext(n)[0]+".webp")
        if not os.path.exists(out) or os.path.getmtime(out)<os.path.getmtime(p):
            subprocess.run(["ffmpeg","-y","-loglevel","error","-ss","2","-i",p,"-frames:v","1","-vf","scale=720:-2","-q:v","70",out])
        if os.path.exists(out):done.append(n)
json.dump(done,open("data/thumbs.json","w"))
print(len(done),"previews")
