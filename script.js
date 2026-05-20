console.log("Beta Phi Alumni Association — Est. 1938 🔱");

// ===============================
// 1. Auto Highlight Active Nav Link
// ===============================
(() => {
  const currentPage = window.location.pathname.split("/").pop() || "index.html";
  const links = document.querySelectorAll(".nav-links a, .nav-mobile a");
  links.forEach(link => {
    const href = link.getAttribute("href");
    if (href === currentPage) {
      link.classList.add("active");
    }
  });
})();

// ===============================
// 2. Scroll Reveal (Fade Up)
// ===============================
(() => {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
        }
      });
    },
    { threshold: 0.12 }
  );
  document.querySelectorAll(".fade-up").forEach(el => observer.observe(el));
})();

// ===============================
// 3. Sticky Nav Shadow on Scroll
// ===============================
(() => {
  const nav = document.getElementById("siteNav");
  if (!nav) return;
  window.addEventListener("scroll", () => {
    if (window.scrollY > 40) {
      nav.style.boxShadow = "0 4px 20px rgba(0,0,0,0.4)";
    } else {
      nav.style.boxShadow = "none";
    }
  });
})();
