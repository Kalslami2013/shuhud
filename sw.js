/* Shuhud service worker: network first, always.
   Online, every page and data file comes fresh from the site exactly as before (the design never changes because of this file).
   Offline, the last copy this phone saw is shown instead, so opened pieces can still be read. */
const C="shuhud-v1";
self.addEventListener("install",()=>self.skipWaiting());
self.addEventListener("activate",e=>e.waitUntil((async()=>{for(const k of await caches.keys())if(k!==C)await caches.delete(k);await self.clients.claim()})()));
const FONT=/^https:\/\/fonts\.(googleapis|gstatic)\.com\//;
self.addEventListener("fetch",e=>{
  const r=e.request;if(r.method!=="GET")return;
  const u=new URL(r.url),same=u.origin===location.origin;
  if(!same&&!FONT.test(r.url))return;
  if(same&&(/\/version\.txt$/.test(u.pathname)||/\.(mp4|webm|mov)$/i.test(u.pathname)||r.headers.has("range")))return;
  const key=same?u.origin+u.pathname:r.url;
  e.respondWith((async()=>{
    try{
      const res=await fetch(r);
      if(res.ok&&(res.type==="basic"||res.type==="cors")){const n=+res.headers.get("content-length")||0;if(n<4e6){const cp=res.clone();caches.open(C).then(c=>c.put(key,cp)).catch(()=>{})}}
      return res;
    }catch(err){
      const c=await caches.open(C);
      const hit=await c.match(key)||(r.mode==="navigate"?(await c.match(u.origin+"/")||await c.match(u.origin+"/index.html")):null);
      if(hit)return hit;
      throw err;
    }
  })());
});
