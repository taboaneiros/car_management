"""
Views for the checklists app.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
)

from apps.vehicles.models import Vehicle

from .forms import ChecklistInspectionForm
from .models import (
    ChecklistInspection,
    ChecklistInspectionItem,
    ChecklistTemplate,
    InspectionStatus,
    ItemStatus,
)


class ChecklistListView(LoginRequiredMixin, ListView):
    """List of checklist inspections with summary metrics."""
    model = ChecklistInspection
    template_name = "checklists/checklist_list.html"
    context_object_name = "inspections"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            ChecklistInspection.objects.filter(
                vehicle__owner_primary=self.request.user
            )
            .select_related("vehicle", "template")
            .order_by("-checked_at")
        )

        vehicle_id = self.request.GET.get("vehicle")
        if vehicle_id:
            qs = qs.filter(vehicle_id=vehicle_id)

        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)

        date_start = self.request.GET.get("date_start")
        if date_start:
            qs = qs.filter(checked_at__date__gte=date_start)

        date_end = self.request.GET.get("date_end")
        if date_end:
            qs = qs.filter(checked_at__date__lte=date_end)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()

        metrics = qs.aggregate(
            total=Count("id"),
            approved=Count("id", filter=Q(status=InspectionStatus.APPROVED)),
            pending=Count("id", filter=Q(status=InspectionStatus.PENDING)),
            warning=Count("id", filter=Q(status=InspectionStatus.WARNING)),
            rejected=Count("id", filter=Q(status=InspectionStatus.REJECTED)),
        )
        context["total_count"] = metrics["total"] or 0
        context["approved_count"] = metrics["approved"] or 0
        context["pending_count"] = metrics["pending"] or 0
        context["warning_count"] = metrics["warning"] or 0
        context["rejected_count"] = metrics["rejected"] or 0

        context["vehicles"] = Vehicle.objects.filter(
            owner_primary=self.request.user, is_active=True
        )
        context["statuses"] = InspectionStatus.choices
        context["selected_vehicle"] = self.request.GET.get("vehicle", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["date_start"] = self.request.GET.get("date_start", "")
        context["date_end"] = self.request.GET.get("date_end", "")
        return context


class ChecklistCreateView(LoginRequiredMixin, CreateView):
    """Interactive checklist execution view."""
    model = ChecklistInspection
    form_class = ChecklistInspectionForm
    template_name = "checklists/checklist_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        vehicle_id = self.request.GET.get("vehicle")
        if vehicle_id:
            kwargs["vehicle"] = get_object_or_404(
                Vehicle, id=vehicle_id, owner_primary=self.request.user
            )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        template_id = self.request.GET.get("template")
        template = None
        if template_id:
            template = ChecklistTemplate.objects.filter(
                Q(user=self.request.user) | Q(is_system=True),
                id=template_id,
            ).first()

        if not template:
            template = ChecklistTemplate.objects.filter(
                Q(user=self.request.user) | Q(is_system=True),
                is_active=True,
            ).first()

        context["current_template"] = template
        items = list(template.items.all().order_by("order", "title")) if template else []
        
        # Group items by category
        categories = {}
        for item in items:
            cat = item.category or "Geral"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        context["grouped_items"] = categories
        context["item_statuses"] = ItemStatus.choices
        return context

    def form_valid(self, form):
        inspection = form.save(commit=False)

        # 1. Resolve template
        template = inspection.template
        if not template:
            template_id = self.request.POST.get("template") or self.request.GET.get("template")
            if template_id:
                template = ChecklistTemplate.objects.filter(
                    Q(user=self.request.user) | Q(is_system=True),
                    id=template_id,
                ).first()
            if not template:
                template = ChecklistTemplate.objects.filter(
                    Q(user=self.request.user) | Q(is_system=True),
                    is_active=True,
                ).first()
            inspection.template = template

        inspection.save()

        # 2. Parse all evaluated items from POST data
        from .models import ChecklistTemplateItem
        evaluated_items = []
        for key, val in self.request.POST.items():
            if key.startswith("item_status_"):
                item_pk = key.replace("item_status_", "")
                note_val = self.request.POST.get(f"item_notes_{item_pk}", "").strip()
                evaluated_items.append((item_pk, val, note_val))

        if evaluated_items:
            t_items = {
                str(t.id): t for t in ChecklistTemplateItem.objects.filter(
                    id__in=[e[0] for e in evaluated_items]
                )
            }
            for item_pk, status_val, note_val in evaluated_items:
                t_item = t_items.get(item_pk)
                category = t_item.category if t_item else "Geral"
                title = t_item.title if t_item else "Item"
                ChecklistInspectionItem.objects.create(
                    inspection=inspection,
                    category=category,
                    title=title,
                    status=status_val,
                    notes=note_val,
                )
        elif template:
            for item in template.items.all():
                status_key = f"item_status_{item.id}"
                notes_key = f"item_notes_{item.id}"

                item_status = self.request.POST.get(status_key, ItemStatus.OK)
                item_notes = self.request.POST.get(notes_key, "").strip()

                ChecklistInspectionItem.objects.create(
                    inspection=inspection,
                    category=item.category,
                    title=item.title,
                    status=item_status,
                    notes=item_notes,
                )

        inspection.evaluate_status()
        inspection.save()

        messages.success(self.request, f"Inspeção '{inspection.title}' registrada com sucesso!")
        return redirect("checklists:detail", pk=inspection.pk)


class ChecklistDetailView(LoginRequiredMixin, DetailView):
    """View details of a completed checklist inspection."""
    model = ChecklistInspection
    template_name = "checklists/checklist_detail.html"
    context_object_name = "inspection"

    def get_queryset(self):
        return ChecklistInspection.objects.filter(
            vehicle__owner_primary=self.request.user
        ).select_related("vehicle", "template").prefetch_related("items")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        items = list(self.object.items.all().order_by("category", "title"))

        grouped = {}
        for item in items:
            cat = item.category or "Geral"
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(item)

        context["grouped_items"] = grouped
        context["problem_items"] = [i for i in items if i.status == ItemStatus.PROBLEM]
        context["attention_items"] = [i for i in items if i.status == ItemStatus.ATTENTION]
        return context


class ChecklistDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    """Delete a checklist inspection."""
    model = ChecklistInspection
    template_name = "checklists/checklist_confirm_delete.html"
    context_object_name = "inspection"
    success_url = reverse_lazy("checklists:list")
    success_message = "Inspeção excluída com sucesso."

    def get_queryset(self):
        return ChecklistInspection.objects.filter(
            vehicle__owner_primary=self.request.user
        )

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

