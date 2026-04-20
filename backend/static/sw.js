/**
 * AutoJustice AI NEXUS — Service Worker (PWA)
 * Phase 2: Enables offline complaint drafting and background sync.
 *
 * Strategy:
 *   - Static assets (CSS, JS, fonts): Cache-first with 7-day TTL
 *   - API calls: Network-first, offline fallback from cache
 *   - Complaint drafts: Stored in IndexedDB via the citizen portal JS
 *   - Background sync: Queued offline submissions sent when connection restores
 */

const CACHE_NAME    = 'autojustice-v2';
const OFFLINE_URL   = '/offline.html';
const API_PREFIX    = '/api/';

// Assets to pre-cache at install time (app shell)
const PRECACHE_URLS = [
  '/',
  '/track',
  '/static/css/main.css',
  '/static/js/citizen.js',
  '/static/manifest.json',
];

// ── Install ─────────────────────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_URLS).catch((err) => {
        console.warn('[SW] Pre-cache failed for some URLs:', err);
      });
    })
  );
  self.skipWaiting();
});

// ── Activate ─────────────────────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// ── Fetch ─────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET and cross-origin requests
  if (request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }

  // API calls: network-first (fresh data), cache as fallback
  if (url.pathname.startsWith(API_PREFIX)) {
    event.respondWith(networkFirstWithCache(request));
    return;
  }

  // Static assets: cache-first (fast load)
  if (
    url.pathname.startsWith('/static/') ||
    url.pathname === '/manifest.json'
  ) {
    event.respondWith(cacheFirstWithNetwork(request));
    return;
  }

  // HTML pages: network-first, offline fallback
  event.respondWith(networkFirstWithOfflineFallback(request));
});

// ── Background Sync (offline form submission) ─────────────────────────────────
self.addEventListener('sync', (event) => {
  if (event.tag === 'submit-complaint') {
    event.waitUntil(syncPendingComplaints());
  }
});

async function syncPendingComplaints() {
  try {
    const db = await openDraftDB();
    const drafts = await getAllDrafts(db);
    for (const draft of drafts) {
      try {
        const resp = await fetch('/api/reports/submit', {
          method: 'POST',
          body: draft.formData,
        });
        if (resp.ok) {
          await deleteDraft(db, draft.id);
          // Notify all open windows of successful sync
          const clients = await self.clients.matchAll({ type: 'window' });
          clients.forEach((client) =>
            client.postMessage({
              type: 'SYNC_SUCCESS',
              caseData: resp.json(),
              draftId: draft.id,
            })
          );
        }
      } catch (err) {
        console.warn('[SW] Sync failed for draft', draft.id, err);
      }
    }
  } catch (err) {
    console.error('[SW] Background sync error:', err);
  }
}

// ── Push Notifications (future: case status updates) ─────────────────────────
self.addEventListener('push', (event) => {
  if (!event.data) return;
  try {
    const data = event.data.json();
    const options = {
      body: data.body || 'Your case has been updated.',
      icon: '/static/icons/icon-192.png',
      badge: '/static/icons/icon-192.png',
      data: { url: data.url || '/track' },
      actions: [
        { action: 'track', title: 'Track Case' },
        { action: 'dismiss', title: 'Dismiss' },
      ],
      vibrate: [200, 100, 200],
      requireInteraction: data.requireInteraction || false,
    };
    event.waitUntil(
      self.registration.showNotification(
        data.title || 'AutoJustice AI NEXUS',
        options
      )
    );
  } catch (err) {
    console.error('[SW] Push notification error:', err);
  }
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'dismiss') return;
  const url = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(
    self.clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((clients) => {
        const existing = clients.find((c) => c.url === url);
        if (existing) return existing.focus();
        return self.clients.openWindow(url);
      })
  );
});

// ── Cache Strategies ──────────────────────────────────────────────────────────

async function cacheFirstWithNetwork(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('Asset unavailable offline', { status: 503 });
  }
}

async function networkFirstWithCache(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    return cached || new Response(
      JSON.stringify({ error: 'Offline — data unavailable', offline: true }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

async function networkFirstWithOfflineFallback(request) {
  try {
    return await fetch(request);
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    // Try to serve offline page
    const offline = await caches.match(OFFLINE_URL);
    return offline || new Response(
      '<h1>You are offline</h1><p>Please check your internet connection.</p>',
      { headers: { 'Content-Type': 'text/html' } }
    );
  }
}

// ── IndexedDB Helpers for Offline Draft Storage ───────────────────────────────

function openDraftDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('autojustice-drafts', 1);
    req.onupgradeneeded = (e) => {
      e.target.result.createObjectStore('drafts', { keyPath: 'id', autoIncrement: true });
    };
    req.onsuccess = (e) => resolve(e.target.result);
    req.onerror   = (e) => reject(e.target.error);
  });
}

function getAllDrafts(db) {
  return new Promise((resolve, reject) => {
    const tx   = db.transaction('drafts', 'readonly');
    const req  = tx.objectStore('drafts').getAll();
    req.onsuccess = (e) => resolve(e.target.result || []);
    req.onerror   = (e) => reject(e.target.error);
  });
}

function deleteDraft(db, id) {
  return new Promise((resolve, reject) => {
    const tx  = db.transaction('drafts', 'readwrite');
    const req = tx.objectStore('drafts').delete(id);
    req.onsuccess = () => resolve();
    req.onerror   = (e) => reject(e.target.error);
  });
}
