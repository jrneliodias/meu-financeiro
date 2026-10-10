// Positions [popover][data-menu] action menus under the button that opened them
// (or above, if there's no room). 'toggle' doesn't bubble, so listen in capture phase.
document.addEventListener('toggle', (e) => {
    const menu = e.target;
    if (e.newState !== 'open' || !menu.matches('[data-menu]')) return;
    const rect = document.querySelector(`[popovertarget="${menu.id}"]`).getBoundingClientRect();
    const fitsBelow = rect.bottom + menu.offsetHeight + 8 < window.innerHeight;
    menu.style.top = `${fitsBelow ? rect.bottom + 4 : rect.top - menu.offsetHeight - 4}px`;
    menu.style.left = `${Math.max(8, rect.right - menu.offsetWidth)}px`;
}, true);

// A fixed menu would detach from its button on scroll (page or modal), so just close it.
document.addEventListener('scroll', () => {
    document.querySelector('[data-menu]:popover-open')?.hidePopover();
}, { capture: true, passive: true });
