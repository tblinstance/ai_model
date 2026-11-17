/**
 * Motion One animation helpers with safe fallback if CDN is unavailable.
 */
window.AIModelMotion = (() => {
  function animateEntrance(selector) {
    const elements = document.querySelectorAll(selector);
    if (!elements.length) return;
    if (window.Motion && typeof window.Motion.animate === "function") {
      window.Motion.animate(
        elements,
        { opacity: [0, 1], transform: ["translateY(10px)", "translateY(0px)"] },
        { duration: 0.35, easing: "ease-out" }
      );
    }
  }

  function pulseElement(el) {
    if (!el || !window.Motion || typeof window.Motion.animate !== "function") return;
    window.Motion.animate(
      el,
      { transform: ["scale(0.98)", "scale(1.02)", "scale(1)"] },
      { duration: 0.3 }
    );
  }

  return { animateEntrance, pulseElement };
})();

