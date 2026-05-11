const CACHE_NAME = "reference-check-web-v7";
const APP_SHELL = [
  "./",
  "./index.html",
  "./styles.css",
  "./verified-links.css?v=pages-v2",
  "./app.js?v=pages-v2",
  "./app.v2.bundle.01.b64",
  "./app.v2.bundle.02.b64",
  "./app.v2.bundle.03.b64",
  "./app.v2.bundle.04.b64",
  "./app.v2.bundle.05.b64",
  "./app.v2.bundle.06.b64",
  "./app.v2.bundle.07.b64",
  "./app.v2.bundle.08.b64",
  "./app.v2.bundle.09.b64",
  "./app.v2.bundle.10.b64",
  "./app.v2.bundle.11.b64",
  "./app.v2.bundle.12.b64",
  "./app.v2.bundle.13.b64",
  "./app.v2.bundle.14.b64",
  "./app.v2.bundle.15.b64",
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
