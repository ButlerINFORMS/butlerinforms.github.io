(() => {
  const button = document.querySelector('.menu-button');
  const nav = document.querySelector('.mobile-nav');
  if (button && nav) {
    button.addEventListener('click', () => {
      const open = nav.classList.toggle('open');
      button.setAttribute('aria-expanded', String(open));
    });
  }
  document.addEventListener('dragstart', e => {
    if (e.target.closest('.protected-media, .protected-image')) e.preventDefault();
  });
  document.addEventListener('contextmenu', e => {
    if (e.target.closest('.protected-media, .protected-image')) e.preventDefault();
  });
})();
