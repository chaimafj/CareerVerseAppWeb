self.addEventListener('push', event => {
  let payload;
  try {
    payload = event.data?.json();
  } catch (error) {
    console.error('Invalid CareerVerse push payload', error);
    return;
  }
  if (!payload || typeof payload.title !== 'string' || typeof payload.body !== 'string') {
    console.error('Missing CareerVerse notification fields');
    return;
  }
  event.waitUntil(self.registration.showNotification(payload.title, {
    body:payload.body,
    icon:'/favicon.svg',
    tag:payload.tag || 'careerverse',
    data:{path:payload.path},
  }));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const path = event.notification.data?.path;
  const safePath = typeof path === 'string' && /^\/(results\/\d+|recommendations|notifications)\/?$/.test(path) ? path : '/notifications';
  const url = new URL(safePath, self.location.origin).href;
  event.waitUntil((async () => {
    const tabs = await self.clients.matchAll({type:'window',includeUncontrolled:true});
    for (const tab of tabs) {
      if (new URL(tab.url).origin === self.location.origin && 'navigate' in tab) {
        await tab.navigate(url);
        return tab.focus();
      }
    }
    return self.clients.openWindow(url);
  })());
});
