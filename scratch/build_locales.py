import struct
import os
from pathlib import Path

def generate_mo(messages: dict, output_path: str):
    """
    Generate a GNU gettext .mo file from a dictionary of msgid -> msgstr.
    """
    keys = sorted(messages.keys())
    offsets = []
    ids = b""
    strs = b""

    for key in keys:
        val = messages[key]
        key_bytes = key.encode("utf-8") + b"\0"
        val_bytes = val.encode("utf-8") + b"\0"
        offsets.append((len(ids), len(key_bytes) - 1, len(strs), len(val_bytes) - 1))
        ids += key_bytes
        strs += val_bytes

    key_table = []
    val_table = []
    keystart = 7 * 4 + len(keys) * 8 * 2
    valstart = keystart + len(ids)

    for o1, l1, o2, l2 in offsets:
        key_table += [l1, keystart + o1]
        val_table += [l2, valstart + o2]

    header = struct.pack(
        "Iiiiiii",
        0x950412DE,  # Magic number
        0,           # Version
        len(keys),   # Number of strings
        7 * 4,       # Offset of table with original strings
        7 * 4 + len(keys) * 8,  # Offset of table with translation strings
        0,           # Size of hashing table
        0,           # Offset of hashing table
    )

    data = header + struct.pack(f"{len(key_table)}i", *key_table) + struct.pack(f"{len(val_table)}i", *val_table) + ids + strs

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(data)

def generate_po(messages: dict, output_path: str, lang: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f'''msgid ""
msgstr ""
"Project-Id-Version: Car Management\\n"
"POT-Creation-Date: 2026-09-30 01:00+0000\\n"
"PO-Revision-Date: 2026-09-30 01:00+0000\\n"
"Language-Team: \\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Language: {lang}\\n"

''')
        for msgid, msgstr in messages.items():
            if not msgid:
                continue
            clean_id = msgid.replace('"', '\\"')
            clean_str = msgstr.replace('"', '\\"')
            f.write(f'msgid "{clean_id}"\n')
            f.write(f'msgstr "{clean_str}"\n\n')

HEADER = "Project-Id-Version: Car Management\nContent-Type: text/plain; charset=UTF-8\nContent-Transfer-Encoding: 8bit\n"

# Translations dictionary: source -> {pt-br, en, es}
TRANSLATIONS = {
    # Common
    "": {"pt-br": HEADER, "en": HEADER, "es": HEADER},
    "Dashboard": {"pt-br": "Dashboard", "en": "Dashboard", "es": "Panel de Control"},
    "Veículos": {"pt-br": "Veículos", "en": "Vehicles", "es": "Vehículos"},
    "Abastecimentos": {"pt-br": "Abastecimentos", "en": "Refuelings", "es": "Repostajes"},
    "Despesas": {"pt-br": "Despesas", "en": "Expenses", "es": "Gastos"},
    "Manutenções": {"pt-br": "Manutenções", "en": "Maintenances", "es": "Mantenimientos"},
    "Lembretes": {"pt-br": "Lembretes", "en": "Reminders", "es": "Recordatorios"},
    "Viagens": {"pt-br": "Viagens", "en": "Trips", "es": "Viajes"},
    "Checklists": {"pt-br": "Checklists", "en": "Checklists", "es": "Listas de Comprobación"},
    "Relatórios": {"pt-br": "Relatórios", "en": "Reports", "es": "Informes"},
    "Gestão": {"pt-br": "Gestão", "en": "Management", "es": "Gestión"},
    "Tipos de Serviço": {"pt-br": "Tipos de Serviço", "en": "Service Types", "es": "Tipos de Servicio"},
    "Categorias de Despesa": {"pt-br": "Categorias de Despesa", "en": "Expense Categories", "es": "Categorías de Gasto"},
    "Importar Drivvo": {"pt-br": "Importar Drivvo", "en": "Import Drivvo", "es": "Importar Drivvo"},
    "Meu Perfil": {"pt-br": "Meu Perfil", "en": "My Profile", "es": "Mi Perfil"},
    "Novo": {"pt-br": "Novo", "en": "New", "es": "Nuevo"},
    "Salvar": {"pt-br": "Salvar", "en": "Save", "es": "Guardar"},
    "Cancelar": {"pt-br": "Cancelar", "en": "Cancel", "es": "Cancelar"},
    "Excluir": {"pt-br": "Excluir", "en": "Delete", "es": "Eliminar"},
    "Editar": {"pt-br": "Editar", "en": "Edit", "es": "Editar"},
    "Voltar": {"pt-br": "Voltar", "en": "Back", "es": "Volver"},
    "Exportar": {"pt-br": "Exportar", "en": "Export", "es": "Exportar"},
    
    # Reminders
    "Veículo": {"pt-br": "Veículo", "en": "Vehicle", "es": "Vehículo"},
    "Título / Descrição": {"pt-br": "Título / Descrição", "en": "Title / Description", "es": "Título / Descripción"},
    "Tipo de Lembrete": {"pt-br": "Tipo de Lembrete", "en": "Reminder Type", "es": "Tipo de Recordatorio"},
    "Tipo de Serviço": {"pt-br": "Tipo de Serviço", "en": "Service Type", "es": "Tipo de Servicio"},
    "Data Limite": {"pt-br": "Data Limite", "en": "Due Date", "es": "Fecha Límite"},
    "Odômetro Limite (km)": {"pt-br": "Odômetro Limite (km)", "en": "Due Odometer (km)", "es": "Odómetro Límite (km)"},
    "Avisar com antecedência (dias)": {"pt-br": "Avisar com antecedência (dias)", "en": "Alert days before", "es": "Avisar con días de anticipación"},
    "Avisar com antecedência (km)": {"pt-br": "Avisar com antecedência (km)", "en": "Alert km before", "es": "Avisar con km de anticipación"},
    "Repetir este lembrete periodicamente": {"pt-br": "Repetir este lembrete periodicamente", "en": "Recurring reminder", "es": "Repetir este recordatorio periódicamente"},
    "Repetir a cada (meses)": {"pt-br": "Repetir a cada (meses)", "en": "Repeat every (months)", "es": "Repetir cada (meses)"},
    "Repetir a cada (km)": {"pt-br": "Repetir a cada (km)", "en": "Repeat every (km)", "es": "Repetir cada (km)"},
    "Enviar notificação por e-mail": {"pt-br": "Enviar notificação por e-mail", "en": "Send notification by email", "es": "Enviar notificación por correo"},
    "Observações": {"pt-br": "Observações", "en": "Notes", "es": "Observaciones"},
    "Identificação do Lembrete": {"pt-br": "Identificação do Lembrete", "en": "Reminder Identification", "es": "Identificación del Recordatorio"},
    "Critérios de Vencimento (Data ou Odômetro)": {"pt-br": "Critérios de Vencimento (Data ou Odômetro)", "en": "Due Criteria (Date or Odometer)", "es": "Criterios de Vencimiento (Fecha u Odómetro)"},
    "Recorrência e Notificações": {"pt-br": "Recorrência e Notificações", "en": "Recurrence & Notifications", "es": "Recurrencia y Notificaciones"},
    "Salvar Lembrete": {"pt-br": "Salvar Lembrete", "en": "Save Reminder", "es": "Guardar Recordatorio"},
    "Lembrete agendado com sucesso!": {"pt-br": "Lembrete agendado com sucesso!", "en": "Reminder scheduled successfully!", "es": "¡Recordatorio programado con éxito!"},
    "Lembrete atualizado com sucesso!": {"pt-br": "Lembrete atualizado com sucesso!", "en": "Reminder updated successfully!", "es": "¡Recordatorio actualizado con éxito!"},
    "Lembrete excluído com sucesso.": {"pt-br": "Lembrete excluído com sucesso.", "en": "Reminder deleted successfully.", "es": "Recordatorio eliminado con éxito."},
    "Manutenção": {"pt-br": "Manutenção", "en": "Maintenance", "es": "Mantenimiento"},
    "Despesa / Imposto": {"pt-br": "Despesa / Imposto", "en": "Expense / Tax", "es": "Gasto / Impuesto"},
    "Documento / CNH / IPVA": {"pt-br": "Documento / CNH / IPVA", "en": "Document / License", "es": "Documento / Licencia"},
    "Outro": {"pt-br": "Outro", "en": "Other", "es": "Otro"},
    "Pendente": {"pt-br": "Pendente", "en": "Pending", "es": "Pendiente"},
    "Concluído": {"pt-br": "Concluído", "en": "Completed", "es": "Completado"},
    "Cancelado": {"pt-br": "Cancelado", "en": "Cancelled", "es": "Cancelado"},
    
    # Checklists
    "Inspeções e Checklists": {"pt-br": "Inspeções e Checklists", "en": "Inspections and Checklists", "es": "Inspecciones y Listas"},
    "Aprovado": {"pt-br": "Aprovado", "en": "Approved", "es": "Aprobado"},
    "Atenção (com ressalvas)": {"pt-br": "Atenção (com ressalvas)", "en": "Attention (with warnings)", "es": "Atención (con reservas)"},
    "Reprovado (não conforme)": {"pt-br": "Reprovado (não conforme)", "en": "Rejected (non-conforming)", "es": "Reprobado (no conforme)"},
}

base_dir = Path("/home/carlos/Público/Projetos de Software/App_Car_Management/car_management")

for lang_code, folder in [("pt-br", "pt_BR"), ("en", "en"), ("es", "es")]:
    lang_msgs = {k: v[lang_code] for k, v in TRANSLATIONS.items()}
    po_file = base_dir / "locale" / folder / "LC_MESSAGES" / "django.po"
    mo_file = base_dir / "locale" / folder / "LC_MESSAGES" / "django.mo"
    generate_po(lang_msgs, str(po_file), lang_code)
    generate_mo(lang_msgs, str(mo_file))
    print(f"Generated {po_file} and {mo_file}")
