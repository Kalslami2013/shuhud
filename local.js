/* «الشهود» standalone runtime: stands in for the Claude viewer.
   Pieces and the tracker come from data/*.json on this site (filled by Claude and by the hourly RSS job),
   merged with what you add yourself on this device (kept in the browser's IndexedDB). */
(function(){
  const DBN="shuhud-local",ST="docs";
  const idb=new Promise((ok,no)=>{const r=indexedDB.open(DBN,1);r.onupgradeneeded=()=>r.result.createObjectStore(ST);r.onsuccess=()=>ok(r.result);r.onerror=()=>no(r.error)});
  const tx=async(mode,fn)=>{const d=await idb;return new Promise((ok,no)=>{const t=d.transaction(ST,mode),s=t.objectStore(ST);const r=fn(s);t.oncomplete=()=>ok(r&&r.result);t.onerror=()=>no(t.error)})};
  const getAll=async()=>{const d=await idb;return new Promise((ok,no)=>{const out={},t=d.transaction(ST,"readonly"),c=t.objectStore(ST).openCursor();c.onsuccess=()=>{const cur=c.result;if(cur){out[cur.key]=cur.value;cur.continue()}else ok(out)};c.onerror=()=>no(c.error)})};
  const put=(k,v)=>tx("readwrite",s=>s.put(v,k)),del=k=>tx("readwrite",s=>s.delete(k));
  const uid=()=>Date.now().toString(36)+Math.random().toString(36).slice(2,8);

  const FILES={dispatches:["data/pieces.json"],monitor:["data/monitor.json","data/feed.json"]};
  const remote={dispatches:[],monitor:[]},subs=[];let remoteAt={};
  async function loadRemote(col){const parts=await Promise.all(FILES[col].map(async f=>{try{const r=await fetch(f+"?t="+Date.now(),{cache:"no-store"});return r.ok?await r.json():null}catch(e){return null}}));if(parts.some(Boolean)){remote[col]=parts.filter(Boolean).flat();remoteAt[col]=new Date()}}
  async function merged(col){
    const loc=await getAll();const map=new Map();
    (remote[col]||[]).forEach(d=>map.set(d.id,{...d,_remote:true}));
    Object.entries(loc).forEach(([k,v])=>{if(!k.startsWith(col+"/"))return;const id=k.slice(col.length+1);if(v&&v.__deleted)map.delete(id);else map.set(id,{...(map.get(id)||{}),...v,id})});
    return [...map.values()];
  }
  async function notify(){for(const s of subs){try{s.run()}catch(e){}}}
  function snap(list){const docs=list.map(d=>({id:d.id,exists:true,data:()=>{const {id,...rest}=d;return rest},metadata:{}}));return {docs,size:docs.length,empty:!docs.length,docChanges:()=>[],metadata:{}}}
  function query(col,ord,dir,lim){return {
    orderBy:(f,d="asc")=>query(col,f,d,lim),limit:n=>query(col,ord,dir,n),where:()=>query(col,ord,dir,lim),
    async get(){let l=await merged(col);if(ord)l.sort((a,b)=>String(a[ord]||"")<String(b[ord]||"")?(dir==="desc"?1:-1):(dir==="desc"?-1:1));if(lim)l=l.slice(0,lim);return snap(l)},
    onSnapshot(next,err){const s={run:async()=>{try{next(await this.get())}catch(e){err&&err(e)}}};s.run=s.run.bind(this);subs.push(s);s.run();return ()=>{const k=subs.indexOf(s);if(k>=0)subs.splice(k,1)}},
    doc(id=uid()){return {id,path:col+"/"+id,
      async set(data){await put(col+"/"+id,data);notify()},
      async update(data){const cur=(await merged(col)).find(d=>d.id===id)||{};const {_remote,...base}=cur;await put(col+"/"+id,{...base,...data});notify()},
      async delete(){await put(col+"/"+id,{__deleted:true});notify()},
      async get(){const d=(await merged(col)).find(x=>x.id===id);return {id,exists:!!d,data:()=>d,metadata:{}}},
      onSnapshot(next){(async()=>{const d=(await merged(col)).find(x=>x.id===id);next({id,exists:!!d,data:()=>d,metadata:{}})})();return ()=>{}}
    }},
    async add(data){const r=this.doc();await r.set(data);return r},
    collection(){return query(col)}
  }}
  const db={collection:col=>query(col)};

  async function refresh(){await Promise.all(Object.keys(FILES).map(loadRemote));notify();window.dispatchEvent(new CustomEvent("shuhud-remote",{detail:remoteAt}))}
  refresh();setInterval(refresh,10*60*1000);document.addEventListener("visibilitychange",()=>{if(!document.hidden)refresh()});

  /* photos: kept in this browser as data URLs */
  const assets={async upload(blob){const url=await new Promise((ok,no)=>{const r=new FileReader();r.onload=()=>ok(r.result);r.onerror=no;r.readAsDataURL(blob)});return {id:uid(),url,sizeBytes:blob.size,contentType:blob.type}},async delete(){},async list(){return {assets:[],usage:{}}}};

  /* files: a normal browser download */
  const downloads={async save({filename,data}){const b=data instanceof Blob?data:new Blob([data]);const u=URL.createObjectURL(b);const a=document.createElement("a");a.href=u;a.download=filename;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),4000);return {status:"saved"}}};

  /* writing with AI: optional, only with your own Anthropic API key (billed separately from the Claude plan) */
  const KEY="shuhud-api-key",MODEL="claude-sonnet-5-5";
  const getKey=()=>{try{return localStorage.getItem(KEY)||""}catch(e){return ""}};
  async function b64(blob){return await new Promise(ok=>{const r=new FileReader();r.onload=()=>ok(String(r.result).split(",")[1]);r.readAsDataURL(blob)})}
  async function call(input,opts={}){const key=getKey();if(!key)throw {code:"not_granted",message:"no key"};
    const msgs=typeof input==="string"?[{role:"user",content:input}]:input.map(m=>({...m}));
    if(opts.images){const imgs=Array.isArray(opts.images)?opts.images:[...opts.images];const last=msgs[msgs.length-1];last.content=[...await Promise.all(imgs.map(async im=>({type:"image",source:{type:"base64",media_type:im.type||"image/jpeg",data:await b64(im)}}))),{type:"text",text:last.content}]}
    const r=await fetch("https://api.anthropic.com/v1/messages",{method:"POST",signal:opts.signal,headers:{"content-type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01","anthropic-dangerous-direct-browser-access":"true"},body:JSON.stringify({model:MODEL,max_tokens:8000,messages:msgs})});
    if(!r.ok){const t=await r.text();throw {code:r.status===429?"rate_limited":r.status===401?"not_granted":"error",message:t}}
    const j=await r.json();const text=(j.content||[]).filter(c=>c.type==="text").map(c=>c.text).join("");opts.onText&&opts.onText({text,delta:text});return {text,truncated:j.stop_reason==="max_tokens"}}
  const sample=Object.assign(call,{
    json:async(i,o)=>{const {text}=await call(i,o);const m=text.match(/\{[\s\S]*\}/);if(!m)throw {code:"bad_json",message:"no json"};return JSON.parse(m[0])},
    limits:async()=>({images:{maxCount:4,maxBytes:5e6,mediaTypes:["image/jpeg","image/png","image/webp","image/gif"]}})
  });

  /* new version on the site? reload once, so the home-screen app is never stuck on an old copy */
  async function checkVersion(){try{const r=await fetch("version.txt?t="+Date.now(),{cache:"no-store"});if(!r.ok)return;const v=(await r.text()).trim();
    if(v&&window.SHUHUD_BUILD&&v!==window.SHUHUD_BUILD){const k="shuhud-reloaded-"+v;if(!sessionStorage.getItem(k)){sessionStorage.setItem(k,"1");location.replace(location.pathname+"?v="+v+location.hash)}}}catch(e){}}
  checkVersion();document.addEventListener("visibilitychange",()=>{if(!document.hidden)checkVersion()});
  window.SHUHUD_STANDALONE=true;window.shuhudKey={get:getKey,set:k=>{try{k?localStorage.setItem(KEY,k):localStorage.removeItem(KEY)}catch(e){}}};
  window.shuhudRefresh=refresh;
  window.claude={use:async name=>name==="db"?db:name==="assets"?assets:name==="downloads"?downloads:name==="sample"?(getKey()?sample:null):name==="user"?{isOwner:()=>true,canEdit:()=>true}:null};
})();
