/**
 * Motion utility — guards anime.js calls behind prefers-reduced-motion.
 *
 * CSS animations are already covered by the media query in index.css.
 * This module provides the JavaScript-side guard for anime.js calls.
 */

/**
 * Returns true when the user prefers reduced motion.
 * Checks the live media query so it updates if the user toggles
 * the setting while the app is open.
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Subscribe to changes in the reduced-motion preference.
 * Returns an unsubscribe function.
 */
export function onReducedMotionChange(callback: (reduced: boolean) => void): () => void {
  if (typeof window === 'undefined') return () => {};
  const mql = window.matchMedia('(prefers-reduced-motion: reduce)');
  const handler = (e: MediaQueryListEvent) => callback(e.matches);
  mql.addEventListener('change', handler);
  return () => mql.removeEventListener('change', handler);
}
