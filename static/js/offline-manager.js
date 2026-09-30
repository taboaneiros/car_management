/**
 * Car Management — Offline Sync Manager & PWA Bridge
 * Handles service worker lifecycle, offline form interception, background auto-sync,
 * and user notifications.
 */
(function (window, document) {
  'use strict';

  const SYNC_RECORDS_URL = '/api/sync/records/';
  const SYNC_BOOTSTRAP_URL = '/api/sync/bootstrap/';

  let isSyncing = false;

  // --------------------------------------------------------------------------
  // Helpers
  // --------------------------------------------------------------------------
  function getCsrfToken() {
    const meta = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (meta) return meta.value;
    const cookies = document.cookie ? document.cookie.split(';') : [];
    for (let c of cookies) {
      const trimmed = c.trim();
      if (trimmed.startsWith('csrftoken=')) {
        return decodeURIComponent(trimmed.substring(10));
      }
    }
    return '';
  }

  function showToast(title, message, type = 'info') {
    const stack = document.querySelector('.cm-toast-stack');
    if (!stack) return;

    const toast = document.createElement('div');
    toast.className = `toast cm-toast toast-${type} show`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    const iconMap = {
      success: 'bi-check-circle-fill text-success',
      danger: 'bi-x-octagon-fill text-danger',
      warning: 'bi-exclamation-triangle-fill text-warning',
      info: 'bi-info-circle-fill text-primary',
    };

    toast.innerHTML = `
      <div class="toast-body d-flex align-items-center gap-2">
        <i class="bi ${iconMap[type] || iconMap.info} fs-5"></i>
        <div class="flex-grow-1">
          <div class="fw-semibold small">${title}</div>
          <div class="small">${message}</div>
        </div>
        <button type="button" class="btn-close ms-1" style="font-size:.7rem" data-bs-dismiss="toast" aria-label="Fechar"></button>
      </div>
    `;

    stack.appendChild(toast);
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 400);
    }, 5000);
  }

  // --------------------------------------------------------------------------
  // UI Network Pill & Queue Indicators
  // --------------------------------------------------------------------------
  async function updateNetworkStatusUI() {
    const isOnline = navigator.onLine;
    let pendingCount = 0;
    try {
      if (window.OfflineDB) {
        pendingCount = await window.OfflineDB.getPendingCount();
      }
    } catch (e) { /* ignore */ }

    // Update Desktop & Mobile Pills
    const pills = document.querySelectorAll('.cm-network-pill');
    pills.forEach((pill) => {
      if (!isOnline) {
        pill.className = 'cm-network-pill badge bg-warning-subtle text-warning border border-warning-subtle';
        pill.innerHTML = `<i class="bi bi-cloud-slash me-1"></i>Offline${pendingCount > 0 ? ` (${pendingCount})` : ''}`;
        pill.setAttribute('title', 'Você está offline. Os registros são salvos localmente.');
      } else if (pendingCount > 0) {
        pill.className = 'cm-network-pill badge bg-info-subtle text-info border border-info-subtle';
        pill.innerHTML = `<i class="bi bi-cloud-arrow-up me-1"></i>Sincronizar (${pendingCount})`;
        pill.setAttribute('title', `${pendingCount} registro(s) aguardando sincronização com o servidor.`);
      } else {
        pill.className = 'cm-network-pill badge bg-success-subtle text-success border border-success-subtle d-none d-lg-inline-flex';
        pill.innerHTML = `<i class="bi bi-wifi me-1"></i>Online`;
        pill.setAttribute('title', 'Conectado à internet.');
      }
    });

    // Update bottom nav badge on menu if offline items exist
    const menuBadge = document.querySelector('#cmMobileMenuBadge');
    if (menuBadge) {
      if (pendingCount > 0) {
        menuBadge.style.display = 'inline-block';
        menuBadge.textContent = pendingCount;
      } else {
        menuBadge.style.display = 'none';
      }
    }
  }

  // --------------------------------------------------------------------------
  // Bootstrap Cache Sync (Seed reference data for offline forms)
  // --------------------------------------------------------------------------
  async function refreshBootstrapCache() {
    if (!navigator.onLine || !window.OfflineDB) return;
    try {
      const response = await fetch(SYNC_BOOTSTRAP_URL, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      if (response.ok) {
        const data = await response.json();
        if (data.vehicles) await window.OfflineDB.setBootstrap('vehicles', data.vehicles);
        if (data.fuel_types) await window.OfflineDB.setBootstrap('fuel_types', data.fuel_types);
        if (data.categories) await window.OfflineDB.setBootstrap('categories', data.categories);
        if (data.service_types) await window.OfflineDB.setBootstrap('service_types', data.service_types);
        if (data.checklist_templates) await window.OfflineDB.setBootstrap('checklist_templates', data.checklist_templates);
      }
    } catch (e) {
      console.warn('[OfflineManager] Não foi possível atualizar bootstrap cache:', e);
    }
  }

  // Populate empty selects if user navigates while offline
  async function populateOfflineFormSelects() {
    if (navigator.onLine || !window.OfflineDB) return;

    // Check vehicle select
    const vehicleSelect = document.querySelector('select[name="vehicle"]');
    if (vehicleSelect && vehicleSelect.options.length <= 1) {
      const vehicles = await window.OfflineDB.getBootstrap('vehicles');
      if (vehicles && vehicles.length) {
        vehicleSelect.innerHTML = '<option value="">Selecione um veículo...</option>';
        vehicles.forEach((v) => {
          const opt = document.createElement('option');
          opt.value = v.id;
          opt.textContent = `${v.name} (${v.plate || v.model})`;
          vehicleSelect.appendChild(opt);
        });
      }
    }

    // Check category select (for expenses)
    const categorySelect = document.querySelector('select[name="category"]');
    if (categorySelect && categorySelect.options.length <= 1) {
      const categories = await window.OfflineDB.getBootstrap('categories');
      if (categories && categories.length) {
        categorySelect.innerHTML = '<option value="">Selecione uma categoria...</option>';
        categories.forEach((c) => {
          const opt = document.createElement('option');
          opt.value = c.id;
          opt.textContent = c.name;
          categorySelect.appendChild(opt);
        });
      }
    }

    // Check service type select (for maintenance/reminders)
    const serviceTypeSelect = document.querySelector('select[name="service_type"]');
    if (serviceTypeSelect && serviceTypeSelect.options.length <= 1) {
      const serviceTypes = await window.OfflineDB.getBootstrap('service_types');
      if (serviceTypes && serviceTypes.length) {
        serviceTypeSelect.innerHTML = '<option value="">Selecione o tipo de serviço...</option>';
        serviceTypes.forEach((s) => {
          const opt = document.createElement('option');
          opt.value = s.id;
          opt.textContent = s.name;
          serviceTypeSelect.appendChild(opt);
        });
      }
    }
  }

  // --------------------------------------------------------------------------
  // Form Interception (Capture records offline)
  // --------------------------------------------------------------------------
  function detectEntityTypeFromForm(form) {
    const action = form.getAttribute('action') || window.location.pathname;
    if (action.includes('/fuel/') || window.location.pathname.includes('/fuel/')) return 'fuel';
    if (action.includes('/expenses/') || window.location.pathname.includes('/expenses/')) return 'expense';
    if (action.includes('/maintenance/') || window.location.pathname.includes('/maintenance/')) return 'maintenance';
    if (action.includes('/reminders/') || window.location.pathname.includes('/reminders/')) return 'reminder';
    if (action.includes('/checklists/') || window.location.pathname.includes('/checklists/')) return 'checklist';
    if (action.includes('/trips/') || window.location.pathname.includes('/trips/')) return 'trip';
    return null;
  }

  function serializeFormToPayload(form) {
    const formData = new FormData(form);
    const payload = {};

    for (let [key, value] of formData.entries()) {
      if (key === 'csrfmiddlewaretoken') continue;
      // Handle file attachments (if any)
      if (value instanceof File) {
        continue; // Binary attachments queued separately
      }
      payload[key] = value;
    }

    // Extract dynamic checklist radio items if applicable
    if (form.querySelectorAll('input[type="radio"][name^="item_status_"]').length > 0) {
      payload.items = [];
      const radios = form.querySelectorAll('input[type="radio"][name^="item_status_"]:checked');
      radios.forEach((r) => {
        const itemId = r.name.replace('item_status_', '');
        const noteInput = form.querySelector(`input[name="item_notes_${itemId}"]`);
        payload.items.push({
          template_item_id: itemId,
          status: r.value,
          notes: noteInput ? noteInput.value : '',
        });
      });
    }

    return payload;
  }

  function initOfflineFormInterception() {
    document.addEventListener('submit', async function (e) {
      const form = e.target;
      if (!form || form.tagName !== 'FORM') return;

      const entityType = detectEntityTypeFromForm(form);
      if (!entityType) return; // Not an entity creation form

      // Only intercept if offline or connection fails
      if (!navigator.onLine) {
        e.preventDefault();
        e.stopPropagation();

        const payload = serializeFormToPayload(form);
        if (!payload.vehicle) {
          alert('Por favor, selecione um veículo antes de salvar.');
          return;
        }

        try {
          await window.OfflineDB.enqueue(entityType, payload);
          showToast(
            'Salvo Offline com Sucesso! 💾',
            `O registro foi armazenado no seu aparelho e será enviado automaticamente assim que a conexão retornar.`,
            'warning'
          );
          updateNetworkStatusUI();

          // Smooth redirect after 1.2s to relevant list
          setTimeout(() => {
            const redirectMap = {
              fuel: '/fuel/',
              expense: '/expenses/',
              maintenance: '/maintenance/',
              reminder: '/reminders/',
              checklist: '/checklists/',
              trip: '/trips/',
            };
            window.location.href = redirectMap[entityType] || '/';
          }, 1200);
        } catch (err) {
          console.error('[OfflineManager] Erro ao salvar offline:', err);
          alert('Erro ao armazenar registro localmente: ' + err.message);
        }
      }
    });
  }

  // --------------------------------------------------------------------------
  // Background Auto-Sync Engine
  // --------------------------------------------------------------------------
  async function triggerAutoSync() {
    if (isSyncing || !navigator.onLine || !window.OfflineDB) return;

    const pending = await window.OfflineDB.getPending();
    if (!pending || pending.length === 0) {
      updateNetworkStatusUI();
      return;
    }

    isSyncing = true;
    showToast(
      'Sincronizando... 🔄',
      `Enviando ${pending.length} registro(s) pendente(s) para o servidor...`,
      'info'
    );

    try {
      const response = await fetch(SYNC_RECORDS_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({ records: pending }),
      });

      if (!response.ok) {
        throw new Error(`Servidor retornou status HTTP ${response.status}`);
      }

      const result = await response.json();
      let syncedCount = 0;

      for (let res of (result.results || [])) {
        if (res.status === 'synced') {
          await window.OfflineDB.remove(res.id);
          syncedCount++;
        } else {
          await window.OfflineDB.updateStatus(res.id, 'error', res.message);
        }
      }

      if (syncedCount > 0) {
        showToast(
          'Sincronização Concluída! 🚀',
          `${syncedCount} registro(s) sincronizado(s) com sucesso com o servidor.`,
          'success'
        );
        // Dispatch custom event for views to refresh
        window.dispatchEvent(new CustomEvent('cm:records-synced', { detail: result }));
      }

      updateNetworkStatusUI();
    } catch (err) {
      console.warn('[OfflineManager] Falha ao sincronizar lote:', err);
      showToast(
        'Falha na Sincronização ⚠️',
        'Não foi possível enviar os registros agora. Uma nova tentativa será feita em breve.',
        'danger'
      );
    } finally {
      isSyncing = false;
      updateNetworkStatusUI();
    }
  }

  // --------------------------------------------------------------------------
  // Modal de Detalhes da Fila de Sincronização
  // --------------------------------------------------------------------------
  window.openOfflineSyncModal = async function () {
    const modalEl = document.getElementById('cmOfflineSyncModal');
    if (!modalEl) return;

    const listEl = document.getElementById('cmOfflineQueueList');
    const countEl = document.getElementById('cmOfflineModalCount');
    const syncBtn = document.getElementById('cmOfflineModalSyncBtn');

    if (!window.OfflineDB) return;
    const pending = await window.OfflineDB.getPending();

    if (countEl) countEl.textContent = `${pending.length} pendente(s)`;

    if (listEl) {
      if (pending.length === 0) {
        listEl.innerHTML = `
          <div class="text-center py-4 text-muted">
            <i class="bi bi-cloud-check fs-1 text-success d-block mb-2"></i>
            <p class="mb-0 fw-semibold">Tudo sincronizado!</p>
            <small>Não há nenhum registro aguardando envio.</small>
          </div>
        `;
        if (syncBtn) syncBtn.disabled = true;
      } else {
        const labels = {
          fuel: 'Abastecimento',
          expense: 'Despesa',
          maintenance: 'Manutenção',
          reminder: 'Lembrete',
          checklist: 'Checklist',
          trip: 'Viagem',
        };
        const icons = {
          fuel: 'bi-fuel-pump text-success',
          expense: 'bi-cash-stack text-warning',
          maintenance: 'bi-tools text-primary',
          reminder: 'bi-bell text-warning',
          checklist: 'bi-card-checklist text-info',
          trip: 'bi-geo-alt text-secondary',
        };

        listEl.innerHTML = pending.map((item) => `
          <div class="list-group-item d-flex align-items-center justify-content-between py-2 px-3">
            <div class="d-flex align-items-center gap-2">
              <i class="bi ${icons[item.entity_type] || 'bi-circle'} fs-5"></i>
              <div>
                <div class="fw-semibold small">${labels[item.entity_type] || item.entity_type}</div>
                <div class="text-muted" style="font-size:.75rem">
                  ${new Date(item.created_offline_at).toLocaleTimeString('pt-BR')} · ${item.payload.description || item.payload.station_name || item.payload.title || 'Novo registro'}
                </div>
              </div>
            </div>
            <span class="badge ${item.status === 'error' ? 'bg-danger' : 'bg-warning text-dark'} small">
              ${item.status === 'error' ? 'Erro' : 'Pendente'}
            </span>
          </div>
        `).join('');

        if (syncBtn) syncBtn.disabled = !navigator.onLine;
      }
    }

    if (window.bootstrap && window.bootstrap.Modal) {
      const modal = new window.bootstrap.Modal(modalEl);
      modal.show();
    }
  };

  // --------------------------------------------------------------------------
  // Mobile Form Ergonomics & Keypad Helpers
  // --------------------------------------------------------------------------
  function enhanceMobileFormInputs() {
    const decimalFields = [
      'liters', 'price_per_liter', 'total_amount', 'amount', 'total_cost',
      'cost', 'price', 'latitude', 'longitude', 'distance'
    ];
    const numericFields = [
      'odometer', 'odometer_reading', 'target_odometer', 'current_odometer',
      'trigger_odometer', 'due_odometer', 'recurrence_interval_km',
      'recurrence_interval_months', 'default_interval_km', 'default_interval_months', 'year'
    ];

    decimalFields.forEach((name) => {
      document.querySelectorAll(`input[name="${name}"]`).forEach((input) => {
        if (!input.hasAttribute('inputmode')) input.setAttribute('inputmode', 'decimal');
      });
    });

    numericFields.forEach((name) => {
      document.querySelectorAll(`input[name="${name}"]`).forEach((input) => {
        if (!input.hasAttribute('inputmode')) input.setAttribute('inputmode', 'numeric');
      });
    });
  }

  // --------------------------------------------------------------------------
  // Initialization
  // --------------------------------------------------------------------------
  function init() {
    // 1. Register Service Worker
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker
        .register('/sw.js', { scope: '/' })
        .then((reg) => console.log('[PWA] Service Worker registrado com escopo:', reg.scope))
        .catch((err) => console.warn('[PWA] Falha ao registrar Service Worker:', err));
    }

    // 2. Listen to network changes
    window.addEventListener('online', () => {
      showToast('Conexão Restabelecida! 🌐', 'Você está online novamente. Verificando sincronizações...', 'success');
      updateNetworkStatusUI();
      triggerAutoSync();
      refreshBootstrapCache();
    });

    window.addEventListener('offline', () => {
      showToast('Modo Offline Ativado 📡', 'Você está sem internet. Novos registros serão salvos localmente.', 'warning');
      updateNetworkStatusUI();
      populateOfflineFormSelects();
    });

    // 3. Init form interception and bootstrap
    initOfflineFormInterception();
    enhanceMobileFormInputs();
    updateNetworkStatusUI();

    if (navigator.onLine) {
      refreshBootstrapCache();
      triggerAutoSync();
    } else {
      populateOfflineFormSelects();
    }

    // Periodic check every 45s if online
    setInterval(() => {
      if (navigator.onLine) triggerAutoSync();
    }, 45000);
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Export public API
  window.OfflineManager = {
    triggerSync: triggerAutoSync,
    updateStatus: updateNetworkStatusUI,
    refreshBootstrap: refreshBootstrapCache,
  };
})(window, document);

