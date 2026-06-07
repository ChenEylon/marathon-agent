self.addEventListener('push', event => {
  const data = event.data?.json() ?? {}
  const title = data.title || 'Marathon Coach'
  const body = data.body || data.full || ''
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: '/favicon.svg',
      badge: '/favicon.svg',
      data: { full: data.full },
    })
  )
})

self.addEventListener('notificationclick', event => {
  event.notification.close()
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      if (list.length) return list[0].focus()
      return clients.openWindow('/')
    })
  )
})
