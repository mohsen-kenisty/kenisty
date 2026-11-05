// يخزّن الصفحة والمكتبات على الجهاز علشان البرنامج يفتح من غير نت. غيّر V عند كل تحديث كبير.
const V='kenisty-v4';
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(['./','index.html','manifest.webmanifest'])));self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==V).map(x=>caches.delete(x)))));self.clients.claim()});
self.addEventListener('fetch',e=>{const r=e.request,u=new URL(r.url);
 if(r.method!=='GET'||/firestore\.googleapis|identitytoolkit|securetoken/.test(u.hostname))return;   // لا نكاش بيانات الحساب والقاعدة
 e.respondWith(caches.open(V).then(async c=>{const m=await c.match(r);
  const f=fetch(r).then(x=>{if(x.ok)c.put(r,x.clone());return x}).catch(()=>m);   // يعرض المخزّن فورًا ويحدّثه في الخلفية
  return m||f}))});
