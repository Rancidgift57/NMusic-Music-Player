// Define a name for the cache
const CACHE_NAME = 'nmusic-player-v2'; // Incremented cache version
const API_CACHE_NAME = 'nmusic-api-cache-v1';

// List all the files and assets that need to be cached for offline use
const urlsToCache = [
  '/',
  '/index.html',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap'
];

// --- INSTALL EVENT ---
// This event is triggered when the service worker is first installed.
// It opens the cache and adds all the specified files to it.
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened app shell cache');
        return cache.addAll(urlsToCache);
      })
  );
});

// --- FETCH EVENT ---
// This event is triggered for every network request the page makes.
self.addEventListener('fetch', event => {
  const { url, method } = event.request;

  // We only want to cache GET requests.
  if (method !== 'GET') {
    return;
  }

  // --- API Caching Strategy (Stale-While-Revalidate) ---
  // This handles requests to your API.
  if (url.includes('nmusic.onrender.com')) {
    event.respondWith(
      caches.open(API_CACHE_NAME).then(cache => {
        // 1. Try to fetch from the network first.
        return fetch(event.request).then(networkResponse => {
          // If the network request is successful, cache it and return it.
          // This ensures the cache is always updated with the latest data.
          cache.put(event.request, networkResponse.clone());
          return networkResponse;
        }).catch(() => {
          // 2. If the network fails (e.g., server is sleeping, user is offline),
          // try to serve the response from the cache.
          return cache.match(event.request);
        });
      })
    );
    return; // End execution for API requests here.
  }

  // --- App Shell Caching Strategy (Cache First) ---
  // For all other assets (HTML, CSS, JS), serve from cache if available.
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // If the response is found in the cache, return it.
        if (response) {
          return response;
        }
        // Otherwise, fetch the resource from the network.
        return fetch(event.request);
      })
  );
});


// --- ACTIVATE EVENT ---
// This event is triggered when the service worker is activated.
// It's a good place to clean up old caches.
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME, API_CACHE_NAME]; // Add the new API cache to the whitelist
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
