(async () => {
  const parts = Array.from({ length: 8 }, (_, index) => `app.bundle.${index + 1}.b64`);
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
