/* Offline reading switched off (23 Nov 2026): on iPhones the site stayed on «الغابة صامتة» while loading.
   This version removes itself and its saved copies; the site then works exactly as before the offline feature. */
self.addEventListener("install",()=>self.skipWaiting());
self.addEventListener("activate",e=>e.waitUntil((async()=>{for(const k of await caches.keys())await caches.delete(k);await self.registration.unregister();for(const c of await self.clients.matchAll({type:"window"}))c.navigate(c.url)})()));
