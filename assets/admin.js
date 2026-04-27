let installPrompt = null;

const installTriggers = [
  () => document.getElementById("install-app-trigger"),
  () => document.getElementById("install-app-trigger-mobile"),
  () => document.getElementById("install-app-trigger-drawer"),
];

function setInstallVisibility(visible) {
  installTriggers.forEach((getter) => {
    const node = getter();
    if (!node) return;
    node.dataset.installPromptAvailable = visible ? "true" : "false";
  });
}

function openInstallDrawer() {
  const drawer = document.getElementById("adminInstallDrawer");
  if (!drawer || !window.bootstrap?.Offcanvas) return;
  window.bootstrap.Offcanvas.getOrCreateInstance(drawer).show();
}

async function handleInstallClick(event) {
  event.preventDefault();
  if (!installPrompt) {
    openInstallDrawer();
    return;
  }
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

  setInstallVisibility(false);
});
