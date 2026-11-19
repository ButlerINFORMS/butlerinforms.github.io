(() => {
  const button = document.querySelector('.menu-button');
  const nav = document.querySelector('.mobile-nav');
  if (button && nav) {
    button.addEventListener('click', () => {
      const open = nav.classList.toggle('open');
      button.setAttribute('aria-expanded', String(open));
    });
  }
  document.querySelectorAll('.flyer-expand[aria-controls]').forEach(flyerButton => {
    const dialogId = flyerButton.getAttribute('aria-controls');
    const flyerDialog = dialogId && document.getElementById(dialogId);
    if (flyerDialog && typeof flyerDialog.showModal === 'function') {
      flyerButton.addEventListener('click', () => flyerDialog.showModal());
      flyerDialog.addEventListener('click', e => {
        if (e.target === flyerDialog) flyerDialog.close();
      });
    }
  });
  document.addEventListener('dragstart', e => {
    if (e.target.closest('.protected-media, .protected-image')) e.preventDefault();
  });
  document.addEventListener('contextmenu', e => {
    if (e.target.closest('.protected-media, .protected-image')) e.preventDefault();
  });
})();
