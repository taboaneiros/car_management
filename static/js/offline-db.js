/**
 * Car Management — IndexedDB Offline Engine
 * Manages local storage for offline records queue and reference bootstrap data.
 */
(function (window) {
  'use strict';

  const DB_NAME = 'CarManagementOfflineDB';
  const DB_VERSION = 1;
  const STORE_QUEUE = 'offline_queue';
  const STORE_BOOTSTRAP = 'bootstrap_cache';

  let dbInstance = null;

  function openDatabase() {
    if (dbInstance) return Promise.resolve(dbInstance);

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains(STORE_QUEUE)) {
          const queueStore = db.createObjectStore(STORE_QUEUE, { keyPath: 'id' });
          queueStore.createIndex('status', 'status', { unique: false });
          queueStore.createIndex('created_at', 'created_offline_at', { unique: false });
          queueStore.createIndex('entity_type', 'entity_type', { unique: false });
        }
        if (!db.objectStoreNames.contains(STORE_BOOTSTRAP)) {
          db.createObjectStore(STORE_BOOTSTRAP, { keyPath: 'key' });
        }
      };

      request.onsuccess = (event) => {
        dbInstance = event.target.result;
        resolve(dbInstance);
      };

      request.onerror = (event) => {
        console.error('[OfflineDB] Erro ao abrir IndexedDB:', event.target.error);
        reject(event.target.error);
      };
    });
  }

  const OfflineDB = {
    /**
     * Enqueue an offline record for future synchronization.
     */
    enqueue: async function (entityType, payload) {
      const db = await openDatabase();
      const record = {
        id: (crypto && crypto.randomUUID) ? crypto.randomUUID() : 'rec_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9),
        entity_type: entityType,
        created_offline_at: new Date().toISOString(),
        payload: payload,
        status: 'pending',
        attempts: 0,
        last_error: null,
      };

      return new Promise((resolve, reject) => {
        const tx = db.transaction([STORE_QUEUE], 'readwrite');
        const store = tx.objectStore(STORE_QUEUE);
        const req = store.add(record);

        req.onsuccess = () => resolve(record);
        req.onerror = (e) => reject(e.target.error);
      });
    },

    /**
     * Get all pending records awaiting sync.
     */
    getPending: async function () {
      const db = await openDatabase();
      return new Promise((resolve, reject) => {
        const tx = db.transaction([STORE_QUEUE], 'readonly');
        const store = tx.objectStore(STORE_QUEUE);
        const req = store.getAll();

        req.onsuccess = () => {
          const all = req.result || [];
          resolve(all.filter((r) => r.status === 'pending' || r.status === 'error'));
        };
        req.onerror = (e) => reject(e.target.error);
      });
    },

    /**
     * Count pending records.
     */
    getPendingCount: async function () {
      const pending = await this.getPending();
      return pending.length;
    },

    /**
     * Remove successfully synced record by ID.
     */
    remove: async function (id) {
      const db = await openDatabase();
      return new Promise((resolve, reject) => {
        const tx = db.transaction([STORE_QUEUE], 'readwrite');
        const store = tx.objectStore(STORE_QUEUE);
        const req = store.delete(id);

        req.onsuccess = () => resolve(true);
        req.onerror = (e) => reject(e.target.error);
      });
    },

    /**
     * Update status and error for a record.
     */
    updateStatus: async function (id, status, errorMsg = null) {
      const db = await openDatabase();
      return new Promise((resolve, reject) => {
        const tx = db.transaction([STORE_QUEUE], 'readwrite');
        const store = tx.objectStore(STORE_QUEUE);
        const getReq = store.get(id);

        getReq.onsuccess = () => {
          const record = getReq.result;
          if (record) {
            record.status = status;
            record.last_error = errorMsg;
            record.attempts = (record.attempts || 0) + 1;
            store.put(record);
            resolve(record);
          } else {
            resolve(null);
          }
        };
        getReq.onerror = (e) => reject(e.target.error);
      });
    },

    /**
     * Save reference bootstrap data (vehicles, categories, etc.) for offline usage.
     */
    setBootstrap: async function (key, value) {
      const db = await openDatabase();
      return new Promise((resolve, reject) => {
        const tx = db.transaction([STORE_BOOTSTRAP], 'readwrite');
        const store = tx.objectStore(STORE_BOOTSTRAP);
        const req = store.put({ key: key, value: value, updated_at: new Date().toISOString() });

        req.onsuccess = () => resolve(true);
        req.onerror = (e) => reject(e.target.error);
      });
    },

    /**
     * Get cached bootstrap data.
     */
    getBootstrap: async function (key) {
      const db = await openDatabase();
      return new Promise((resolve, reject) => {
        const tx = db.transaction([STORE_BOOTSTRAP], 'readonly');
        const store = tx.objectStore(STORE_BOOTSTRAP);
        const req = store.get(key);

        req.onsuccess = () => resolve(req.result ? req.result.value : null);
        req.onerror = (e) => reject(e.target.error);
      });
    },
  };

  window.OfflineDB = OfflineDB;
})(window);

