function fadeInPage(el) {
  gsap.fromTo(el, { opacity: 0, y: 15, scale: 0.98 }, { opacity: 1, y: 0, scale: 1, duration: 0.5, ease: "power3.out" });
}

function animateAurora(el) {
  if (!el) return;
  const blobs = el.querySelectorAll('.aurora-blob');
  
  blobs.forEach((blob, i) => {
    // Initial setup
    gsap.set(blob, {
      x: () => gsap.utils.random(-window.innerWidth/4, window.innerWidth),
      y: () => gsap.utils.random(-window.innerHeight/4, window.innerHeight),
    });

    // The slow aurora animation loop
    gsap.to(blob, {
      x: () => gsap.utils.random(-window.innerWidth/4, window.innerWidth),
      y: () => gsap.utils.random(-window.innerHeight/4, window.innerHeight),
      scale: () => gsap.utils.random(1, 1.6),
      rotation: () => gsap.utils.random(0, 180),
      duration: () => gsap.utils.random(20, 35),
      ease: "sine.inOut",
      repeat: -1,
      yoyo: true,
      delay: i * -3,
    });
  });
}

function staggerRows(container) {
  if (!container) return;
  const rows = container.querySelectorAll("tr");
  gsap.fromTo(rows, { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.3, stagger: 0.05, ease: "power2.out" });
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



function animateToastIn(el) {
  if (!el) return;
  gsap.fromTo(el, { opacity: 0, x: 40 }, { opacity: 1, x: 0, duration: 0.3, ease: "power2.out" });
}

function shakeElement(el) {
  if (!el) return;
  gsap.fromTo(el, { x: -6 }, { x: 0, duration: 0.4, ease: "elastic.out(1, 0.3)" });
}

function staggerCards(container) {
  if (!container) return;
  gsap.fromTo(
    container.children,
    { opacity: 0, y: 20, scale: 0.95 },
    { opacity: 1, y: 0, scale: 1, duration: 0.5, stagger: 0.1, ease: "power3.out" }
  );
}

function animateBarsIn(container) {
  if (!container) return;
  const bars = container.querySelectorAll("[data-bar-target]");
  if (!bars.length) return;
  gsap.fromTo(
    bars,
    { width: "0%" },
    {
      width: (_, el) => el.dataset.barTarget + "%",
      duration: 0.8,
      ease: "power2.out",
      stagger: 0.06,
      delay: 0.1,
    }
  );
}

function animateMarkersIn(container) {
  if (!container) return;
  const markers = container.querySelectorAll("[data-marker-target]");
  if (!markers.length) return;
  gsap.fromTo(
    markers,
    { left: "0%", opacity: 0 },
    {
      left: (_, el) => el.dataset.markerTarget + "%",
      opacity: 1,
      duration: 0.9,
      ease: "power3.out",
      delay: 0.3,
    }
  );
}
