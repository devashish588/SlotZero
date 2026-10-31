document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('form').forEach((form) => {
    form.addEventListener('submit', (event) => {
      const message = form.getAttribute('data-confirm');
      if (form.getAttribute('aria-busy') === 'true' || (message && !window.confirm(message))) {
        event.preventDefault();
        return;
      }
      form.setAttribute('aria-busy', 'true');
      if (event.submitter) event.submitter.setAttribute('aria-disabled', 'true');
    });
  });

  window.addEventListener('pageshow', () => {
    document.querySelectorAll('form[aria-busy="true"]').forEach((form) => {
      form.removeAttribute('aria-busy');
      form.querySelectorAll('[aria-disabled="true"]').forEach((button) => button.removeAttribute('aria-disabled'));
    });
  });

  document.querySelectorAll('.copy-demo').forEach((button) => {
    button.addEventListener('click', () => {
      const email = document.querySelector('input[name="email"]');
      const password = document.querySelector('input[name="password"]');
      if (email && password) {
        email.value = button.dataset.copyEmail;
        password.value = button.dataset.copyPassword;
        password.focus();
      }
    });
  });

  const clock = document.getElementById('local-clock');
  if (clock && window.Intl) {
    const zone = clock.textContent.trim();
    const update = () => {
      try {
        clock.textContent = new Intl.DateTimeFormat('en-GB', {
          timeZone: zone, hour: '2-digit', minute: '2-digit', weekday: 'short',
        }).format(new Date());
      } catch (_) { /* Keep the zone label if the browser cannot format it. */ }
    };
    update();
    window.setInterval(update, 30000);
  }

  // Timezone selector functionality
  const timezoneSelector = document.getElementById('timezone-selector');
  if (timezoneSelector) {
    const trigger = document.getElementById('timezone-trigger');
    const dropdown = document.getElementById('timezone-dropdown');
    const display = document.getElementById('timezone-display');
    const saving = document.getElementById('timezone-saving');
    const message = document.getElementById('timezone-message');
    const options = dropdown.querySelectorAll('.timezone-option');
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;

    let isSubmitting = false;

    function closeDropdown() {
      dropdown.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
    }

    function openDropdown() {
      dropdown.hidden = false;
      trigger.setAttribute('aria-expanded', 'true');
    }

    function showSaving() {
      saving.hidden = false;
      trigger.disabled = true;
      options.forEach(opt => opt.disabled = true);
    }

    function hideSaving() {
      saving.hidden = true;
      trigger.disabled = false;
      options.forEach(opt => opt.disabled = false);
    }

    function showMessage(text, isError = false) {
      message.textContent = text;
      message.className = 'timezone-message ' + (isError ? 'error' : 'success');
      message.hidden = false;
      setTimeout(() => { message.hidden = true; }, 5000);
    }

    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      if (dropdown.hidden) openDropdown(); else closeDropdown();
    });

    dropdown.addEventListener('click', (e) => {
      const option = e.target.closest('.timezone-option');
      if (!option || isSubmitting) return;
      const newZone = option.dataset.zone;
      if (newZone === display.textContent.trim()) {
        closeDropdown();
        return;
      }
      isSubmitting = true;
      showSaving();
      closeDropdown();

      const formData = new FormData();
      formData.append('csrf_token', csrfToken);
      formData.append('timezone_name', newZone);

      fetch('/patient/timezone', { method: 'POST', body: formData })
        .then(response => {
          if (response.redirected) {
            return response.text().then(html => {
              const parser = new DOMParser();
              const doc = parser.parseFromString(html, 'text/html');
              const notice = doc.querySelector('[data-notice]');
              if (notice) {
                showMessage(notice.textContent, notice.dataset.noticeType === 'error');
              }
              // Check if there's an error in the URL
              const url = new URL(response.url);
              if (url.searchParams.get('notice_type') === 'error') {
                showMessage(decodeURIComponent(url.searchParams.get('notice') || 'Failed to update time zone'), true);
                return;
              }
              // Success - update display and reload page to refresh appointments
              display.textContent = newZone;
              options.forEach(opt => {
                opt.classList.toggle('selected', opt.dataset.zone === newZone);
                opt.setAttribute('aria-selected', opt.dataset.zone === newZone);
              });
              showMessage('Time zone updated. Reloading appointments…');
              setTimeout(() => window.location.reload(), 1000);
            });
          }
          throw new Error('Unexpected response');
        })
        .catch(err => {
          console.error('Timezone update failed:', err);
          showMessage('Failed to update time zone. Please try again.', true);
        })
        .finally(() => {
          hideSaving();
          isSubmitting = false;
        });
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
      if (!timezoneSelector.contains(e.target)) {
        closeDropdown();
      }
    });

    // Keyboard navigation
    trigger.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeDropdown();
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        if (dropdown.hidden) openDropdown(); else closeDropdown();
      }
    });

    dropdown.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeDropdown();
        trigger.focus();
      }
    });
  }
});
