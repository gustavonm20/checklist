const root = document.documentElement;
const themeToggle = document.querySelector('#theme-toggle');
const themeIcon = document.querySelector('.theme-icon');

function syncThemeIcon() {
  if (!themeIcon) return;
  const isDark = root.dataset.theme === 'dark';
  themeIcon.textContent = isDark ? '☀' : '☾';
  themeToggle?.setAttribute('aria-label', isDark ? 'Ativar modo claro' : 'Ativar modo escuro');
}


if (themeToggle) {
  syncThemeIcon();
  themeToggle.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    localStorage.setItem('checklist-theme', next);
    syncThemeIcon();
  });
}

document.querySelectorAll('.task-toggle').forEach((button) => {
  button.addEventListener('click', async () => {
    const item = button.closest('.task-item');
    if (!item) return;

    button.disabled = true;
    try {
      const response = await fetch(`/tarefas/${item.dataset.taskId}/alternar`, { method: 'POST' });
      if (!response.ok) throw new Error('Não foi possível atualizar a tarefa.');

      const data = await response.json();
      item.classList.toggle('done', data.concluida);
      button.textContent = data.concluida ? '✓' : '';

      const fill = document.querySelector('#progress-fill');
      if (fill) fill.style.width = `${data.progresso}%`;
    } catch (error) {
      console.error(error);
    } finally {
      button.disabled = false;
    }
  });
});
