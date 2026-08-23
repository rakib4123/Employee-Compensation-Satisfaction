function fadeInPage(el) {
  gsap.fromTo(el, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" });
}

function staggerRows(container) {
  if (!container) return;
  const rows = container.querySelectorAll("tr");
  gsap.fromTo(rows, { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.3, stagger: 0.05, ease: "power2.out" });
}

function animateRowIn(row) {
  if (!row) return;
  gsap.fromTo(
    row,
    { opacity: 0, backgroundColor: "rgba(99,102,241,0.15)" },
    { opacity: 1, backgroundColor: "rgba(0,0,0,0)", duration: 0.6, ease: "power2.out" }
  );
}

function animateCountUp(el, target, options = {}) {
  if (!el) return;
  const { prefix = "", decimals = 0 } = options;
  const counter = { value: 0 };
  gsap.to(counter, {
    value: target,
    duration: 1,
    ease: "power1.out",
    onUpdate: () => {
      el.textContent = prefix + counter.value.toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      });
    },
  });
}

function animateModalIn(el) {
  if (!el) return;
  gsap.fromTo(el, { opacity: 0, scale: 0.95 }, { opacity: 1, scale: 1, duration: 0.2, ease: "power2.out" });
}

function animateModalOut(el, onComplete) {
  if (!el) return onComplete && onComplete();
  gsap.to(el, { opacity: 0, scale: 0.95, duration: 0.15, ease: "power1.in", onComplete });
}

function animateToastIn(el) {
  if (!el) return;
  gsap.fromTo(el, { opacity: 0, x: 40 }, { opacity: 1, x: 0, duration: 0.3, ease: "power2.out" });
}

function shakeElement(el) {
  if (!el) return;
  gsap.fromTo(el, { x: -6 }, { x: 0, duration: 0.4, ease: "elastic.out(1, 0.3)" });
}
