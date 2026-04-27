let installPrompt = null;

const installTriggers = [
  () => document.getElementById("install-app-trigger"),
  () => document.getElementById("install-app-trigger-mobile"),
];

function setInstallVisibility(visible) {
  installTriggers.forEach((getter) => {
    const node = getter();
    if (!node) return;
    node.classList.toggle("d-none", !visible);
  });
}

async function handleInstallClick(event) {
  event.preventDefault();
  if (!installPrompt) return;
  installPrompt.prompt();
  await installPrompt.userChoice.catch(() => null);
  installPrompt = null;
  setInstallVisibility(false);
}

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  installPrompt = event;
  setInstallVisibility(true);
});

window.addEventListener("appinstalled", () => {
  installPrompt = null;
  setInstallVisibility(false);
});

window.addEventListener("DOMContentLoaded", () => {
  installTriggers.forEach((getter) => {
    const node = getter();
    if (!node) return;
    node.addEventListener("click", handleInstallClick);
  });

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/assets/sw.js").catch(() => null);
  }
});
