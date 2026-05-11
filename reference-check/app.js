(async () => {
  const parts = [
    'app.v2.bundle.01.b64',
    'app.v2.bundle.02.b64',
    'app.v2.bundle.03.b64',
    'app.v2.bundle.04.b64',
    'app.v2.bundle.05.b64',
    'app.v2.bundle.06.b64',
    'app.v2.bundle.07.b64',
    'app.v2.bundle.08.b64',
    'app.v2.bundle.09.b64',
    'app.v2.bundle.10.b64',
    'app.v2.bundle.11.b64',
    'app.v2.bundle.12.b64',
    'app.v2.bundle.13.b64',
    'app.v2.bundle.14.b64',
    'app.v2.bundle.15.b64',
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
