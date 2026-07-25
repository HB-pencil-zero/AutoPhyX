const results = {
  ficus: {
    left: ["static/videos/ficus-stiff.mp4", "Stiff stems", "The potted plant stays upright and shows only minor shifts in the wind."],
    right: ["static/videos/ficus-flexible.mp4", "Flexible stems", "The plant undergoes pronounced flexible bending and sways deeply to the side."],
  },
  plane: {
    left: ["static/videos/plane-rigid.mp4", "Rigid propeller", "The propeller blades rotate while maintaining their structural integrity."],
    right: ["static/videos/plane-elastic.mp4", "Elastic propeller", "The blades behave like rubber, visibly warping and bending during rotation."],
  },
  toast: {
    left: ["static/videos/toast-intact.mp4", "Structural integrity", "The toast falls while retaining its solid rectangular form and sharp edges."],
    right: ["static/videos/toast-brittle.mp4", "Brittle fracture", "The toast breaks apart and disintegrates on impact."],
  },
  softbody: {
    left: ["static/videos/softbody-bouncy.mp4", "Semi-rigid volume", "The object lands while preserving a bouncy, semi-rigid volume."],
    right: ["static/videos/softbody-soft.mp4", "Large deformation", "The object flattens and spreads like a highly deformable material."],
  },
  can: {
    left: ["static/videos/can-rigid.mp4", "Higher stiffness", "The can keeps more of its original cylindrical structure after impact."],
    right: ["static/videos/can-soft.mp4", "Higher compliance", "The can deforms more readily under the same simulation setup."],
  },
  banana: {
    left: ["static/videos/banana-rigid.mp4", "Firm body", "The banana maintains its overall shape during motion and contact."],
    right: ["static/videos/banana-soft.mp4", "Soft body", "The banana bends more visibly under the same external forces."],
  },
};

const header = document.querySelector("[data-header]");
const menuButton = document.querySelector("[data-menu-button]");
const menu = document.querySelector("[data-menu]");
const tabs = document.querySelectorAll("[data-result]");
const leftVideo = document.querySelector("[data-video-left]");
const rightVideo = document.querySelector("[data-video-right]");
const leftTitle = document.querySelector("[data-title-left]");
const rightTitle = document.querySelector("[data-title-right]");
const leftDescription = document.querySelector("[data-description-left]");
const rightDescription = document.querySelector("[data-description-right]");
const copyButton = document.querySelector("[data-copy-citation]");

function updateHeader() {
  header?.classList.toggle("is-scrolled", window.scrollY > 48);
}

function setMenu(open) {
  menu?.classList.toggle("is-open", open);
  menuButton?.setAttribute("aria-expanded", String(open));
  menuButton?.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
  document.body.classList.toggle("menu-open", open);

  const icon = menuButton?.querySelector("svg");
  if (icon && window.lucide) {
    icon.outerHTML = `<i data-lucide="${open ? "x" : "menu"}" aria-hidden="true"></i>`;
    window.lucide.createIcons();
  }
}

function swapVideo(video, source) {
  if (!video || video.currentSrc.endsWith(source)) return;
  video.src = source;
  video.load();
  video.play().catch(() => {});
}

function selectResult(key) {
  const selected = results[key];
  if (!selected) return;

  tabs.forEach((tab) => tab.setAttribute("aria-selected", String(tab.dataset.result === key)));
  swapVideo(leftVideo, selected.left[0]);
  swapVideo(rightVideo, selected.right[0]);
  leftTitle.textContent = selected.left[1];
  rightTitle.textContent = selected.right[1];
  leftDescription.textContent = selected.left[2];
  rightDescription.textContent = selected.right[2];
}

window.addEventListener("scroll", updateHeader, { passive: true });
updateHeader();

window.addEventListener("load", () => {
  if (!window.location.hash) return;
  const target = document.querySelector(window.location.hash);
  if (!target) return;

  document.documentElement.style.scrollBehavior = "auto";
  target.scrollIntoView();
  window.requestAnimationFrame(() => {
    document.documentElement.style.removeProperty("scroll-behavior");
  });
});

menuButton?.addEventListener("click", () => {
  setMenu(menuButton.getAttribute("aria-expanded") !== "true");
});

menu?.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => setMenu(false)));

tabs.forEach((tab) => {
  tab.addEventListener("click", () => selectResult(tab.dataset.result));
  tab.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const tabList = [...tabs];
    const direction = event.key === "ArrowRight" ? 1 : -1;
    const next = (tabList.indexOf(tab) + direction + tabList.length) % tabList.length;
    tabList[next].focus();
    selectResult(tabList[next].dataset.result);
  });
});

copyButton?.addEventListener("click", async () => {
  const citation = document.querySelector("[data-citation]")?.textContent || "";
  try {
    await navigator.clipboard.writeText(citation);
    copyButton.classList.add("is-copied");
    copyButton.setAttribute("aria-label", "BibTeX copied");
    copyButton.innerHTML = '<i data-lucide="check" aria-hidden="true"></i>';
    window.lucide?.createIcons();
    window.setTimeout(() => {
      copyButton.classList.remove("is-copied");
      copyButton.setAttribute("aria-label", "Copy BibTeX");
      copyButton.innerHTML = '<i data-lucide="copy" aria-hidden="true"></i>';
      window.lucide?.createIcons();
    }, 1800);
  } catch {
    copyButton.setAttribute("aria-label", "Unable to copy BibTeX");
  }
});

window.addEventListener("DOMContentLoaded", () => window.lucide?.createIcons());
