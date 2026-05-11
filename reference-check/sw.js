const CACHE_NAME = "reference-check-web-v6";
const APP_SHELL = [
  "./",
  "./index.html",
  "./styles.css",
  "./app.js?v=pages-v1",
  "./app.bundle.1.b64",
  "./app.bundle.2.b64",
  "./app.bundle.3.b64",
  "./app.bundle.4.b64",
  "./app.bundle.5.b64",
  "./app.bundle.5.tail.b64",
  "./app.bundle.6.b64",
  "./app.bundle.7.b64",
  "./app.bundle.7.tail.b64",
  "./app.bundle.8.b64",
  "./privacy.html",
  "./site.webmanifest",
  "./assets/reference-mark.svg"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match("./index.html"))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request).then((response) => {
      const copy = response.clone();
      caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
      return response;
    }))
  );
});
