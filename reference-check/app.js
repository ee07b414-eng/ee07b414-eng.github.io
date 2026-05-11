(async () => {
  const parts = [
    'app.bundle.1.b64',
    'app.bundle.2.b64',
    'app.bundle.3.b64',
    'app.bundle.4.b64',
    'app.bundle.5.b64',
    'app.bundle.5.tail.b64',
    'app.bundle.6.b64',
    'app.bundle.7.b64',
    'app.bundle.7.tail.b64',
    'app.bundle.8.b64',
  ];
  const encoded = (await Promise.all(parts.map(async (path) => {
    const response = await fetch(path, { cache: 'no-cache' });
    if (!response.ok) throw new Error(`Could not load ${path}`);
    return response.text();
  }))).join('').replace(/\s+/g, '');
  const binary = atob(encoded);
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  const source = new TextDecoder('utf-8').decode(bytes);
  (0, eval)(`${source}\n//# sourceURL=reference-check-main.js`);
})().catch((error) => {
  console.error(error);
  const status = document.querySelector('#input-status');
  if (status) status.textContent = `应用加载失败：${error.message}`;
});
