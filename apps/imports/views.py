"""
Views for the imports app.
"""
import os
import tempfile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import RequestDataTooBig
from django.shortcuts import redirect, render

from .drivvo_parser import (
    extract_expenses,
    extract_refuelings,
    extract_reminders,
    extract_services,
    extract_trips,
    extract_vehicles,
    parse_sections,
)
from .services import import_drivvo_data


@login_required
def import_drivvo(request):
    """
    Import page for Drivvo CSV files.

    Accepts a ``.csv`` file exported from the Drivvo app, parses the supported
    sections (Veículo, Abastecimento, Despesa, Serviço, Lembrete, Percurso) and persists them for the
    current user. Unsupported sections are reported but do not break the
    import.
    """
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")

        if csv_file is None or not csv_file.name.lower().endswith(".csv"):
            messages.error(request, "Por favor, envie um arquivo CSV válido (.csv).")
            return redirect("imports:import_drivvo")

        tmp_path = None
        try:
            # Save the uploaded file to a temporary location so the parser can
            # read it with the detected encoding (Drivvo exports cp1252).
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                for chunk in csv_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            sections = parse_sections(tmp_path)
            parsed_data = {
                "vehicles": extract_vehicles(sections),
                "refuelings": extract_refuelings(sections),
                "expenses": extract_expenses(sections),
                "services": extract_services(sections),
                "reminders": extract_reminders(sections),
                "trips": extract_trips(sections),
                "unsupported_sections": sections.get("unsupported_sections", []),
            }

            result = import_drivvo_data(request.user, parsed_data)

            messages.success(
                request,
                "Importação concluída! "
                f"{result['vehicles_created']} veículos criados, "
                f"{result['vehicles_updated']} atualizados, "
                f"{result['refuelings_created']} abastecimentos, "
                f"{result['expenses_created']} despesas, "
                f"{result['maintenances_created']} manutenções, "
                f"{result['reminders_created']} lembretes e "
                f"{result['trips_created']} viagens importadas.",
            )

            for warning in result["warnings"][:10]:
                messages.warning(request, warning)
            for error in result["errors"][:10]:
                messages.error(request, error)

            return redirect("dashboard:home")

        except RequestDataTooBig:
            messages.error(
                request,
                "O arquivo enviado é muito grande. O tamanho máximo é 10 MB.",
            )
            return redirect("imports:import_drivvo")
        except Exception as exc:  # noqa: BLE001 - show friendly message to the user
            messages.error(request, f"Erro na importação: {exc}")
            return redirect("imports:import_drivvo")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    return render(request, "imports/import_drivvo.html")
