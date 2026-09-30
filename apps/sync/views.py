"""
Views for PWA manifest, Service Worker, bootstrap data and offline synchronization.
"""
import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

from apps.vehicles.models import Vehicle
from apps.fuel.models import FuelType
from apps.expenses.models import ExpenseCategory
from apps.maintenance.models import ServiceType
from apps.checklists.models import ChecklistTemplate
from .services import SyncProcessingService


class PwaManifestView(View):
    """
    Serves the dynamic Web App Manifest (manifest.json).
    """

    def get(self, request, *args, **kwargs):
        manifest_data = {
            "name": "Car Management",
            "short_name": "CarMgmt",
            "description": "Gerenciamento completo e inteligente de veículos, abastecimentos e manutenções.",
            "start_url": "/?source=pwa",
            "scope": "/",
            "display": "standalone",
            "orientation": "portrait-primary",
            "background_color": "#0f172a",
            "theme_color": "#0d6efd",
            "icons": [
                {
                    "src": "/static/icons/icon-192.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any maskable",
                },
                {
                    "src": "/static/icons/icon-512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any maskable",
                },
            ],
            "categories": ["utilities", "productivity", "finance"],
            "shortcuts": [
                {
                    "name": "Novo Abastecimento",
                    "url": "/fuel/create/",
                    "icons": [{"src": "/static/icons/icon-192.png", "sizes": "192x192"}],
                },
                {
                    "name": "Nova Despesa",
                    "url": "/expenses/create/",
                    "icons": [{"src": "/static/icons/icon-192.png", "sizes": "192x192"}],
                },
                {
                    "name": "Nova Manutenção",
                    "url": "/maintenance/create/",
                    "icons": [{"src": "/static/icons/icon-192.png", "sizes": "192x192"}],
                },
            ],
        }
        return JsonResponse(manifest_data, json_dumps_params={"indent": 2})


class ServiceWorkerView(View):
    """
    Serves the Service Worker file from the root scope with proper Service-Worker-Allowed header.
    """

    def get(self, request, *args, **kwargs):
        sw_script = """/* Car Management Service Worker — PWA Cache & Offline Shell */
const CACHE_NAME = 'cm-pwa-v1';
const PRECACHE_ASSETS = [
  '/',
  '/offline/',
  '/static/css/custom.css',
  '/static/js/app.js',
  '/static/js/offline-db.js',
  '/static/js/offline-manager.js',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Sora:wght@600;700;800&display=swap'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS).catch((err) => {
        console.warn('[SW] Falha em alguns itens do pré-cache:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;

  // Ignore non-GET and chrome-extension/internal requests
  if (req.method !== 'GET' || !req.url.startsWith('http')) {
    return;
  }

  // API sync endpoints should never be served from SW cache
  if (req.url.includes('/api/sync/')) {
    return;
  }

  // Static assets (CSS, JS, Fonts, Icons) -> Stale While Revalidate or Cache First
  if (
    req.destination === 'style' ||
    req.destination === 'script' ||
    req.destination === 'font' ||
    req.destination === 'image' ||
    req.url.includes('/static/')
  ) {
    event.respondWith(
      caches.match(req).then((cached) => {
        if (cached) return cached;
        return fetch(req).then((response) => {
          if (response && response.status === 200) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
          }
          return response;
        }).catch(() => caches.match('/offline/'));
      })
    );
    return;
  }

  // HTML page navigations -> Network First with Offline fallback
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then((response) => {
          if (response && response.status === 200) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
          }
          return response;
        })
        .catch(() => {
          return caches.match(req).then((cached) => {
            return cached || caches.match('/offline/');
          });
        })
    );
    return;
  }

  // Default fetch
  event.respondWith(
    fetch(req).catch(() => caches.match(req))
  );
});
"""
        response = HttpResponse(sw_script, content_type="application/javascript")
        response["Service-Worker-Allowed"] = "/"
        response["Cache-Control"] = "no-cache"
        return response


class OfflineFallbackView(TemplateView):
    """
    Renders a friendly offline screen if an uncached route is visited while disconnected.
    """

    template_name = "sync/offline.html"


class OfflineBootstrapDataView(LoginRequiredMixin, View):
    """
    Returns reference data (vehicles, fuel types, categories, service types, checklist templates)
    so the PWA client can seed its local IndexedDB and populate form selectors when offline.
    """

    def get(self, request, *args, **kwargs):
        user = request.user
        vehicles = list(
            Vehicle.objects.filter(owner_primary=user, is_active=True).values(
                "id", "name", "brand", "model", "year", "plate", "current_odometer_cache"
            )
        )
        # Convert UUID to string for JSON serialization
        for v in vehicles:
            v["id"] = str(v["id"])

        fuel_types = list(
            FuelType.objects.filter(is_active=True).values("id", "name", "code")
        )
        for ft in fuel_types:
            ft["id"] = str(ft["id"])

        categories = list(
            ExpenseCategory.objects.filter(user=user, is_active=True).values("id", "name", "slug", "kind")
        )
        for c in categories:
            c["id"] = str(c["id"])

        service_types = list(
            ServiceType.objects.filter(is_active=True).values("id", "name", "default_interval_km", "default_interval_months")
        )
        for st in service_types:
            st["id"] = str(st["id"])

        checklist_templates = []
        for tmpl in ChecklistTemplate.objects.filter(is_active=True).prefetch_related("items"):
            checklist_templates.append({
                "id": str(tmpl.id),
                "name": tmpl.name,
                "description": tmpl.description,
                "items": [
                    {
                        "id": str(it.id),
                        "title": it.title,
                        "category": it.category,
                        "is_required": it.is_required,
                    }
                    for it in tmpl.items.all()
                ],
            })

        data = {
            "user": {
                "id": user.id,
                "email": user.email,
            },
            "vehicles": vehicles,
            "fuel_types": fuel_types,
            "categories": categories,
            "service_types": service_types,
            "checklist_templates": checklist_templates,
            "timestamp": str(request.user.last_login),
        }
        return JsonResponse(data)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class OfflineRecordsSyncView(LoginRequiredMixin, View):
    """
    Receives offline records created by the user and persists them in the server DB.
    """

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"status": "error", "message": "Corpo da requisição JSON inválido."}, status=400)

        records = body.get("records", [])
        if not isinstance(records, list):
            return JsonResponse({"status": "error", "message": "O campo 'records' deve ser uma lista."}, status=400)

        result = SyncProcessingService.process_batch(request.user, records)
        return JsonResponse(result, status=200)
