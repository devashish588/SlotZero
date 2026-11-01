document.addEventListener('DOMContentLoaded', () => {
  const navLinks = Array.from(document.querySelectorAll('.nav-item'));
  const updateWorkspace = () => {
    if (location.pathname === '/doctor/dashboard') {
      document.body.dataset.workspace = location.hash === '#schedule' ? 'schedule' : location.hash === '#blocks' ? 'blocks' : 'overview';
      if (location.hash === '#schedule' || location.hash === '#blocks') {
        requestAnimationFrame(() => document.querySelector(location.hash)?.scrollIntoView({ block: 'start' }));
      }
    }
    let selected = navLinks.find(link => {
      const url = new URL(link.href);
      return url.pathname === location.pathname && url.hash === location.hash;
    });
    if (!selected) selected = navLinks.find(link => location.pathname.startsWith('/appointments/')
      ? new URL(link.href).hash === '#appointments' : !new URL(link.href).hash);
    navLinks.forEach(link => {
      link.classList.toggle('active', link === selected);
      if (link === selected) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  };
  updateWorkspace();
  window.addEventListener('hashchange', updateWorkspace);

  const weeklyEditor = document.getElementById('weekly-editor');
  if (weeklyEditor) {
    const textarea = document.querySelector('[name="schedule_text"]');
    const textField = document.getElementById('schedule-text-field');
    const daysRoot = document.getElementById('weekly-days');
    const toggle = document.getElementById('schedule-text-toggle');
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    let textMode = false;
    const parse = () => {
      const values = days.map(() => []);
      for (const line of textarea.value.split('\n').filter(line => line.trim())) {
        const match = line.trim().match(/^(Mon|Tue|Wed|Thu|Fri|Sat|Sun):\s*(.*)$/);
        if (!match) return null;
        for (const range of match[2].split(',').filter(range => range.trim())) {
          const clocks = range.trim().match(/^(\d{2}:\d{2})-(\d{2}:\d{2})$/);
          if (!clocks) return null;
          values[days.indexOf(match[1])].push([clocks[1], clocks[2]]);
        }
      }
      return values;
    };
    const serialize = () => {
      if (textMode) return;
      textarea.value = days.map((day, index) => {
        const ranges = Array.from(daysRoot.children[index].querySelectorAll('.weekly-range')).map(row => {
          const [start, end] = row.querySelectorAll('input');
          end.setCustomValidity(start.value && end.value && start.value >= end.value ? 'End time must be after start time.' : '');
          return `${start.value}-${end.value}`;
        });
        return `${day}: ${ranges.join(',')}`;
      }).join('\n');
    };
    const addRange = (container, day, clocks = ['', '']) => {
      const row = document.createElement('div');
      row.className = 'weekly-range';
      ['Start', 'End'].forEach((label, index) => {
        const wrapper = document.createElement('label');
        wrapper.textContent = label;
        const input = document.createElement('input');
        input.type = 'time'; input.required = true; input.value = clocks[index];
        input.setAttribute('aria-label', `${day} ${label.toLowerCase()} time`);
        input.addEventListener('input', serialize);
        wrapper.append(input); row.append(wrapper);
      });
      const remove = document.createElement('button');
      remove.type = 'button'; remove.className = 'icon-button'; remove.textContent = '×';
      remove.setAttribute('aria-label', `Remove ${day} working range`);
      remove.addEventListener('click', () => { row.remove(); serialize(); container.nextElementSibling.focus(); });
      row.append(remove); container.append(row);
      return row;
    };
    const renderWeek = values => {
      daysRoot.replaceChildren();
      values.forEach((ranges, index) => {
        const fieldset = document.createElement('fieldset'); fieldset.className = 'weekly-day';
        const legend = document.createElement('legend'); legend.textContent = names[index];
        const container = document.createElement('div'); container.className = 'weekly-ranges';
        const add = document.createElement('button');
        add.type = 'button'; add.className = 'text-action'; add.textContent = 'Add hours';
        add.setAttribute('aria-label', `Add ${names[index]} hours`);
        add.addEventListener('click', () => { addRange(container, names[index]).querySelector('input').focus(); serialize(); });
        fieldset.append(legend, container, add); daysRoot.append(fieldset);
        ranges.forEach(range => addRange(container, names[index], range));
      });
    };
    const initial = parse();
    if (initial) {
      renderWeek(initial); weeklyEditor.hidden = false; textField.hidden = true; textarea.required = false;
      toggle.addEventListener('click', () => {
        if (textMode) {
          const values = parse();
          if (!values) { textarea.setCustomValidity('Use one weekday per line, for example Mon: 09:00-12:00.'); textarea.reportValidity(); return; }
          textarea.setCustomValidity(''); renderWeek(values);
        } else serialize();
        textMode = !textMode;
        textField.hidden = !textMode; daysRoot.hidden = textMode; textarea.required = textMode;
        daysRoot.querySelectorAll('input').forEach(input => input.disabled = textMode);
        toggle.setAttribute('aria-expanded', String(textMode));
        toggle.textContent = textMode ? 'Use day-by-day editor' : 'Edit schedule as text';
        if (textMode) textarea.focus();
      });
      textarea.addEventListener('input', () => textarea.setCustomValidity(''));
      textarea.form.addEventListener('submit', event => {
        serialize();
        if (!textarea.form.reportValidity()) event.preventDefault();
      });
      // Text remains the source of truth for no-script use and existing form clients.
      textarea.addEventListener('input', () => {
        if (!textMode) { const values = parse(); if (values) renderWeek(values); }
      });
    }
  }

  const bell = document.getElementById('notification-bell');
  if (bell) {
    const panel = document.getElementById('notification-panel');
    const status = document.getElementById('notification-status');
    const list = document.getElementById('notification-items');
    const count = document.getElementById('notification-count');
    const toast = document.getElementById('update-toast');
    const key = `slotzero-notifications-${document.body.dataset.userId}`;
    let items = [], seen = null, initialized = false;
    try { const value = localStorage.getItem(key); if (value !== null) seen = Number(value) || 0; } catch (_) { /* Use memory when storage is unavailable. */ }
    const remember = value => { seen = value; try { localStorage.setItem(key, String(value)); } catch (_) { /* In-memory read state still works. */ } };
    const message = item => `${item.actor_name}: appointment ${item.action}.`;
    const showToast = text => {
      document.getElementById('update-toast-message').textContent = text;
      if (panel.hidden) toast.hidden = false;
    };
    toast.querySelector('button').addEventListener('click', () => { toast.hidden = true; bell.focus(); });
    const renderUpdates = () => {
      const unread = items.filter(item => item.id > seen).length;
      count.textContent = String(unread); count.hidden = unread === 0;
      bell.setAttribute('aria-label', unread ? `Notifications, ${unread} unread` : 'Notifications');
      list.replaceChildren();
      items.forEach(item => {
        const li = document.createElement('li');
        const link = document.createElement('a');
        link.href = item.href;
        link.textContent = message(item);
        const time = document.createElement('time'); time.dateTime = item.created_at;
        time.textContent = new Date(item.created_at).toLocaleString(undefined, {timeZone: document.querySelector('.timezone-chip').textContent.trim()});
        li.append(link, time); list.append(li);
      });
      status.textContent = items.length ? 'Recent updates for your appointments.' : 'No appointment updates yet.';
      document.getElementById('notifications-refresh').hidden = items.length === 0;
    };
    const setPanel = open => { panel.hidden = !open; bell.setAttribute('aria-expanded', String(open)); if (open) toast.hidden = true; };
    list.addEventListener('click', event => { if (event.target.closest('a')) setPanel(false); });
    bell.addEventListener('click', () => { setPanel(panel.hidden); if (!panel.hidden) poll(); });
    document.getElementById('notifications-read').addEventListener('click', () => { remember(Math.max(seen || 0, ...items.map(item => item.id))); renderUpdates(); });
    document.getElementById('notifications-refresh').addEventListener('click', () => window.location.reload());
    document.addEventListener('click', event => { if (!event.target.closest('.notification-control')) setPanel(false); });
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && !panel.hidden) { setPanel(false); bell.focus(); } });
    let polling = false;
    async function poll() {
      if (polling || document.hidden) return;
      polling = true;
      try {
        const response = await fetch('/notifications', {headers: {'Accept': 'application/json'}, cache: 'no-store'});
        if (!response.ok || response.redirected) throw new Error('Updates unavailable');
        const data = await response.json();
        const previous = Math.max(0, ...items.map(item => item.id));
        items = data.items;
        const latest = Math.max(0, ...items.map(item => item.id));
        if (seen === null) remember(latest);
        if (latest > seen && (!initialized || latest > previous)) showToast(message(items[0]));
        initialized = true; renderUpdates();
      } catch (_) { status.textContent = 'Could not refresh updates. We will retry; your appointments are unchanged.'; }
      finally { polling = false; }
    }
    poll(); window.setInterval(poll, 15000);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });
    const notice = document.querySelector('.notice');
    if (notice) showToast(notice.textContent.trim());
  }

  const menuToggle = document.querySelector('.menu-toggle');
  const navigation = document.getElementById('workspace-nav');
  if (menuToggle && navigation) {
    const mobile = window.matchMedia('(max-width: 60rem)');
    const setMenu = (open) => {
      navigation.hidden = mobile.matches && !open;
      menuToggle.setAttribute('aria-expanded', String(open));
    };
    menuToggle.hidden = false;
    setMenu(false);
    mobile.addEventListener('change', () => setMenu(false));
    menuToggle.addEventListener('click', () => setMenu(navigation.hidden));
    menuToggle.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && mobile.matches) setMenu(false);
    });
    navigation.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && mobile.matches) {
        setMenu(false);
        menuToggle.focus();
      }
    });
    navigation.addEventListener('click', (event) => {
      if (event.target.closest('a') && mobile.matches) {
        setMenu(false);
        requestAnimationFrame(() => document.getElementById('main-content').focus({ preventScroll: true }));
      }
    });
  }

  const errorNotice = document.querySelector('.notice[role="alert"]');
  if (errorNotice) {
    errorNotice.tabIndex = -1;
    errorNotice.focus();
  }
  document.querySelectorAll('form').forEach((form) => {
    form.addEventListener('submit', (event) => {
      const message = form.getAttribute('data-confirm');
      if (event.defaultPrevented || form.getAttribute('aria-busy') === 'true' || (message && !window.confirm(message))) {
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
      (dropdown.querySelector('[aria-selected="true"]') || options[0]).focus();
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
        trigger.focus();
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
          trigger.focus();
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
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        openDropdown();
      }
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
      const index = Array.from(options).indexOf(document.activeElement);
      if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) {
        e.preventDefault();
        const next = e.key === 'Home' ? 0 : e.key === 'End' ? options.length - 1
          : (index + (e.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length;
        options[next].focus();
      }
      if (e.key === 'Tab') closeDropdown();
    });
  }
});
