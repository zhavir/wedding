/** Progressive enhancement: content stays visible without JS or with reduced motion. */
export function reveal(node: HTMLElement) {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.animate(
            [
              { opacity: 0.2, transform: 'translateY(24px)' },
              { opacity: 1, transform: 'translateY(0)' }
            ],
            { duration: 750, easing: 'cubic-bezier(.2,.65,.3,1)', fill: 'none' }
          );
          observer.unobserve(entry.target);
        }
      }
    },
    { threshold: 0.08 }
  );
  node
    .querySelectorAll(
      '.intro-copy, .story-image, .section-heading, .schedule article, .rsvp-card, .locked-gallery, .countdown h2'
    )
    .forEach((element) => observer.observe(element));
  return {
    destroy() {
      observer.disconnect();
    }
  };
}
