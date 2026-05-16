(async () => {
  const version = "v3";
  const chunkCount = 8;
  const currentScript = document.currentScript;
  const baseUrl = new URL(currentScript?.src || "./app.js", location.href);
  const files = Array.from({ length: chunkCount }, (_, index) => `app.${version}.bundle.${String(index + 1).padStart(2, "0")}.b64`);
  const chunks = await Promise.all(files.map(async (file) => {
    const response = await fetch(new URL(file, baseUrl), { cache: "no-store" });
    if (!response.ok) throw new Error(`Unable to load ${file}: ${response.status}`);
    const text = (await response.text()).replace(/\s+/g, "");
    if (file === "app.v3.bundle.08.b64") {
      return text.replace("OmZhOW9eXxhcHBlbmRpeC", "OmZhOW9lXxhcHBlbmRpeC");
    }
    return text;
  }));
  const binary = atob(chunks.join(""));
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  const code = new TextDecoder().decode(bytes);
  (0, eval)(`${code}\n//# sourceURL=reference-check-app-v3.js`);
})().catch((error) => {
  console.error("Reference Check failed to load", error);
  const status = document.querySelector("#input-status");
  if (status) status.textContent = `应用脚本加载失败：${error.message}`;
});
