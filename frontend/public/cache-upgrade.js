/* Migrate tabs whose older app has no controllerchange reload handler. */
self.addEventListener('activate',event=>{
 event.waitUntil((async()=>{
  await self.clients.claim();
  const clients=await self.clients.matchAll({type:'window',includeUncontrolled:true});
  await Promise.allSettled(clients.map(client=>{
   const url=new URL(client.url);
   if(!url.href.startsWith(self.registration.scope)||url.searchParams.get('release')==='2026.11.10.7')return;
   url.searchParams.set('release','2026.11.10.7');
   return client.navigate(url.href);
  }));
 })());
});

self.addEventListener('notificationclick',event=>{
 event.notification.close();
 event.waitUntil((async()=>{
  const windows=await self.clients.matchAll({type:'window',includeUncontrolled:true});
  const client=windows.find(window=>window.url.startsWith(self.registration.scope));
  if(client)return client.focus();
  return self.clients.openWindow(self.registration.scope);
 })());
});
