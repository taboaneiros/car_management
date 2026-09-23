"""
Drivvo CSV parser for car_management project.

This module provides utilities to parse CSV files exported from the Drivvo
application. The Drivvo CSV format is composed of sequential sections
(``#Veículo``, ``#Abastecimento``, ``#Despesa``, ``#Serviço``, ``#Receita``,
``#Percurso`` and ``#Lembrete``). Each section has its own header row followed
by data rows.

Real Drivvo exports are usually encoded in ``cp1252`` and use ``,`` as the
delimiter with quoted fields. Older/simpler exports may use ``;`` and plain
section markers (e.g. ``Abastecimento;``). This parser detects the encoding and
the delimiter automatically and normalizes the rows into dictionaries.

The module exposes two APIs:

* ``parse_sections`` — returns each supported section as
  ``{"headers": [...], "rows": [...]}`` plus ``unsupported_sections``.
* ``DrivvoParser`` / ``parse_drivvo_csv`` — legacy API returning a flat dict of
  ``{section_key: [row_dict, ...]}``.

Both rely on the same internal parsing logic.
"""
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

# Mapping of Drivvo section names (as they appear in the CSV) to internal keys.
SECTION_MAP = {
    "Veículo": "vehicles",
    "Abastecimento": "refuelings",
    "Despesa": "expenses",
    "Serviço": "services",
    "Receita": "incomes",
    "Percurso": "trips",
    "Lembrete": "reminders",
}

# Alias kept for clarity with the import pipeline.
SECTION_MAPPING = SECTION_MAP

# Sections that the current import pipeline supports.
SUPPORTED_SECTIONS = {"vehicles", "refuelings", "expenses"}

# Vehicle types: Drivvo label -> VehicleType choice value.
VEHICLE_TYPE_MAPPING = {
    "Carro": "car",
    "Moto": "motorcycle",
    "Caminhão": "truck",
    "Van": "van",
    "Ônibus": "bus",
}

# Fuel types: Drivvo label -> canonical FuelType name used in this project.
# The canonical names match the system fuel types seeded by data migration.
FUEL_TYPE_MAPPING = {
    "Gasolina": "Gasolina comum",
    "Gasolina Comum": "Gasolina comum",
    "Gas. Comum": "Gasolina comum",
    "Gasolina Aditivada": "Gasolina aditivada",
    "Gas. Aditivada": "Gasolina aditivada",
    "Etanol": "Etanol",
    "Etanol Aditivado": "Etanol aditivado",
    "Diesel": "Diesel",
    "GNV": "GNV",
    "Elétrico": "Elétrico",
}

# Expense categories: Drivvo label -> canonical ExpenseCategory name.
EXPENSE_CATEGORY_MAPPING = {
    "Conveniência Posto": "Conveniência",
    "Estacionamento": "Estacionamento",
    "Pedágio": "Pedágio",
    "Lavagem": "Lavagem",
    "Multas": "Multas",
    "Multa": "Multas",
    "Seguro": "Seguro",
    "Impostos": "Impostos e taxas",
    "IPVA": "Impostos e taxas",
    "Financiamento": "Financiamento",
    "Prestação": "Financiamento",
    "Filtro de Ar": "Manutenção",
    "Filtro de Óleo": "Manutenção",
    "Troca de Óleo": "Manutenção",
    "Manutenção": "Manutenção",
    "Pneus": "Pneus",
    "Freio": "Freios",
    "Freios": "Freios",
}


class DrivvoParserError(Exception):
    """Base exception for Drivvo parser errors."""

# ---------------------------------------------------------------------------
# Low level helpers
# ---------------------------------------------------------------------------


def _clean(value: Any) -> str:
    """Strip whitespace from a raw CSV cell."""
    return (value or "").strip()


def _clean_header(value: Any) -> str:
    """
    Normalize a header cell.

    Real Drivvo exports sometimes contain cells such as ``  "Preço / gal"``
    where the leading spaces and quotes are literal characters. This strips
    surrounding whitespace and quotes so the header matches the expected name.
    """
    cleaned = (value or "").strip()
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1]
    return cleaned.strip()


def detect_encoding(file_path: str) -> str:
    """
    Detect the encoding of a CSV file.

    Uses chardet when available (it is an optional dependency) and falls back
    to a small heuristic: try ``utf-8-sig``/``utf-8`` and default to ``cp1252``
    (the encoding used by Drivvo exports) otherwise.
    """
    with open(file_path, "rb") as f:
        raw = f.read(10000)

    try:
        import chardet
    except ImportError:  # pragma: no cover - chardet is optional
        chardet = None

    if chardet is not None:
        detected = chardet.detect(raw)
        encoding = detected.get("encoding")
        if encoding:
            normalized = encoding.lower().replace("_", "-")
            if normalized in ("cp1252", "windows-1252", "latin-1", "iso-8859-1"):
                return "cp1252"
            if normalized in ("utf-8", "utf-8-sig", "utf8"):
                return "utf-8-sig"
            return encoding

    for encoding in ("utf-8-sig", "utf-8"):
        try:
            raw.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "cp1252"


def detect_delimiter(lines: List[str], sample_size: int = 15) -> str:
    """
    Detect the CSV field delimiter from a list of text lines.

    Uses ``csv.Sniffer`` first and falls back to counting delimiter
    occurrences.
    """
    sample = "\n".join(lines[:sample_size])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        return dialect.delimiter
    except csv.Error:
        counts = {d: sum(line.count(d) for line in lines[:sample_size]) for d in ",;\t"}
        if any(counts.values()):
            return max(counts, key=counts.get)
        return ","


# ---------------------------------------------------------------------------
# Section parsing
# ---------------------------------------------------------------------------


def _match_section_marker(cells: List[str]) -> Optional[str]:
    """
    Return the section name when ``cells`` is a section marker row.

    A marker row is a row whose first cell matches a section name (optionally
    prefixed with ``#``) and whose remaining cells are all empty.
    """
    if not cells:
        return None
    first = cells[0].strip()
    if any((cell or "").strip() for cell in cells[1:]):
        return None
    candidate = first.lstrip("#").strip()
    if candidate in SECTION_MAP:
        return candidate
    return None


def _match_combined_header(cells: List[str]) -> Optional[Tuple[str, str, List[str]]]:
    """
    Handle the format ``Veículo - Nome do veículo,Ativo,...``.

    In this format the section title is concatenated with the header row.
    Returns ``(section_key, section_name, headers)`` when matched.
    """
    if not cells:
        return None
    first = cells[0].strip()
    for section_name, key in SECTION_MAP.items():
        prefix = section_name + " - "
        if first.startswith(prefix):
            headers = [_clean_header(h) for h in cells]
            headers[0] = headers[0].replace(prefix, "", 1).strip()
            return key, section_name, headers
    return None


def _parse_rows(raw: str, delimiter: str) -> List[List[str]]:
    """Parse raw file text into a list of non-empty cell rows."""
    reader = csv.reader(io.StringIO(raw), delimiter=delimiter)
    return [row for row in reader if any((cell or "").strip() for cell in row)]


def _row_to_dict(headers: List[str], values: List[str]) -> Dict[str, str]:
    """
    Build a row dict from headers and values.

    Drivvo exports repeat some headers for multi-fuel refuelings
    (``Preço / gal``, ``Valor total``, ``Volume`` appear once per fuel). The
    first occurrence is the primary fuel, so we keep it and ignore the
    duplicates.
    """
    row_dict: Dict[str, str] = {}
    for index, header in enumerate(headers):
        value = values[index] if index < len(values) else ""
        row_dict.setdefault(header, value)
    return row_dict


def parse_sections(
    file_path: str,
    encoding: Optional[str] = None,
    delimiter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse a Drivvo CSV file and group data by section.

    Args:
        file_path: Path to the Drivvo CSV file.
        encoding: Optional encoding override (auto-detected when None).
        delimiter: Optional delimiter override (auto-detected when None).

    Returns:
        A dict with one entry per supported section
        ``{"headers": [...], "rows": [row_dict, ...]}`` and an
        ``unsupported_sections`` list with the human-readable names of the
        sections that are present but not supported by the import pipeline.
    """
    detected_encoding = encoding or detect_encoding(file_path)
    with open(file_path, "r", encoding=detected_encoding) as f:
        raw = f.read()

    if delimiter is None:
        raw_lines = [line for line in raw.splitlines() if line.strip()]
        delimiter = detect_delimiter(raw_lines)

    rows = _parse_rows(raw, delimiter)

    sections: Dict[str, Dict[str, Any]] = {}
    unsupported_sections = set()
    current_section: Optional[str] = None
    current_headers: Optional[List[str]] = None
    current_rows: List[Dict[str, str]] = []

    index = 0
    while index < len(rows):
        cells = [_clean(cell) for cell in rows[index]]

        # Flush the previous section before switching.
        marker = _match_section_marker(cells)
        if marker is not None:
            key = SECTION_MAP[marker]
            if current_section and current_headers is not None:
                sections[current_section] = {
                    "headers": current_headers,
                    "rows": current_rows,
                }
            current_section = key if key in SUPPORTED_SECTIONS else None
            current_headers = None
            current_rows = []
            if key not in SUPPORTED_SECTIONS:
                unsupported_sections.add(marker)
            index += 1
            if index < len(rows):
                current_headers = [_clean_header(header) for header in rows[index]]
                while current_headers and current_headers[-1] == "":
                    current_headers.pop()
                index += 1
            continue

        combined = _match_combined_header(cells)
        if combined is not None:
            key, section_name, headers = combined
            if current_section and current_headers is not None:
                sections[current_section] = {
                    "headers": current_headers,
                    "rows": current_rows,
                }
            current_section = key if key in SUPPORTED_SECTIONS else None
            current_headers = headers
            current_rows = []
            while current_headers and current_headers[-1] == "":
                current_headers.pop()
            if key not in SUPPORTED_SECTIONS:
                unsupported_sections.add(section_name)
            index += 1
            continue

        # Regular data row.
        if current_section and current_headers is not None:
            values = [_clean(value) for value in rows[index]]
            current_rows.append(_row_to_dict(current_headers, values))
        index += 1

    # Flush the last section.
    if current_section and current_headers is not None:
        sections[current_section] = {
            "headers": current_headers,
            "rows": current_rows,
        }

    # Ensure every supported section is always present, even when absent from
    # the file, so the import pipeline can rely on a stable structure.
    result = {
        key: sections.get(key, {"headers": [], "rows": []})
        for key in sorted(SUPPORTED_SECTIONS)
    }
    result["unsupported_sections"] = sorted(unsupported_sections)
    return result


# ---------------------------------------------------------------------------
# Value parsing
# ---------------------------------------------------------------------------


def parse_decimal(value: Any) -> Optional[Decimal]:
    """
    Parse a numeric CSV value into a Decimal.

    Drivvo exports use ``.`` as the decimal separator (e.g. ``22.8``), while
    Brazilian spreadsheets use ``1.234,56``. Both formats are handled:

    * when the value contains both separators the rightmost one is the decimal
      separator;
    * when it contains only ``,`` it is treated as the decimal separator;
    * when it contains only ``.`` it is kept as-is (Drivvo decimal separator).
    """
    if value is None:
        return None
    value = str(value).strip().replace("R$", "").strip()
    if not value:
        return None

    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        value = value.replace(",", ".")

    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def parse_date(value: Any) -> Optional[Any]:
    """
    Parse a date cell into a ``datetime.date``.

    Supports ``DD/MM/YYYY HH:MM`` (Drivvo format) as well as a few common
    variations.
    """
    if not value:
        return None
    value = str(value).strip()
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def parse_year(value: Any) -> Optional[int]:
    """Parse a year cell into an int."""
    if not value:
        return None
    value = str(value).strip()
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------


def map_vehicle_type(drivvo_type: Any) -> str:
    """Map a Drivvo vehicle type label to a VehicleType choice value."""
    return VEHICLE_TYPE_MAPPING.get((drivvo_type or "").strip(), "car")


def map_fuel_type(drivvo_fuel: Any) -> str:
    """
    Map a Drivvo fuel label to a canonical FuelType name.

    Unknown labels are returned unchanged so the import service can create the
    fuel type when needed.
    """
    label = (drivvo_fuel or "").strip()
    return FUEL_TYPE_MAPPING.get(label, label)


def map_expense_category(drivvo_category: Any) -> str:
    """
    Map a Drivvo expense category label to a canonical ExpenseCategory name.

    Unknown labels fall back to ``Outros``.
    """
    label = (drivvo_category or "").strip()
    return EXPENSE_CATEGORY_MAPPING.get(label, "Outros")


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def _get(row: Dict[str, str], *keys: str) -> str:
    """Return the first non-empty value for the given header candidates."""
    for key in keys:
        if key in row:
            return row[key]
    return ""


def _section_rows(sections: Dict[str, Any], key: str) -> List[Dict[str, str]]:
    """Return the list of row dicts for a supported section (may be empty)."""
    data = sections.get(key)
    if not data:
        return []
    if isinstance(data, dict):
        return data.get("rows") or []
    return data or []


def extract_vehicles(sections: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract structured vehicle data from parsed sections."""
    vehicles = []
    for row in _section_rows(sections, "vehicles"):
        vehicles.append(
            {
                "name": _get(row, "Nome do veículo", "Nome", "Name"),
                "is_active": _get(row, "Ativo", "Active").lower() == "sim",
                "vehicle_type": map_vehicle_type(
                    _get(row, "Tipo de veículo", "Tipo", "Type")
                ),
                "brand": _get(row, "Marca", "Brand"),
                "model": _get(row, "Modelo", "Model"),
                "plate": _get(row, "Placa", "License Plate", "Plate"),
                "year": parse_year(_get(row, "Ano", "Year")),
                "odometer": parse_decimal(
                    _get(row, "Odômetro (km)", "Odômetro km", "Odômetro", "Odometer")
                )
                or 0,
                "notes": _get(row, "Observação", "Observações", "Notes"),
            }
        )
    return vehicles


def extract_refuelings(sections: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract structured refueling data from parsed sections."""
    refuelings = []
    for row in _section_rows(sections, "refuelings"):
        refuelings.append(
            {
                "vehicle_name": _get(row, "Nome do veículo", "Nome", "Vehicle"),
                "odometer": parse_decimal(
                    _get(row, "Odômetro (km)", "Odômetro km", "Odômetro", "Odometer")
                )
                or 0,
                "occurred_at": parse_date(_get(row, "Data", "Date")),
                "fuel_type_name": _get(
                    row, "Combustível", "Fuel Type", "Combustível 1", "Fuel"
                ),
                "price_per_liter": parse_decimal(
                    _get(row, "Preço / gal", "Preço gal", "Preço", "Price")
                ),
                "total_amount": parse_decimal(
                    _get(row, "Valor total", "Valor", "Total", "Amount")
                ),
                "liters": parse_decimal(
                    _get(row, "Volume", "Litros", "Liters")
                ),
                "is_full_tank": _get(
                    row, "Completou o tanque", "Full Tank", "Tanque cheio"
                ).lower()
                == "sim",
                "station_name": _get(
                    row, "Posto de combustível", "Posto", "Gas Station", "Station"
                ),
                "notes": _get(row, "Observação", "Observações", "Notes"),
            }
        )
    return refuelings


def extract_expenses(sections: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract structured expense data from parsed sections."""
    expenses = []
    for row in _section_rows(sections, "expenses"):
        notes = _get(row, "Observação", "Observações", "Notes")
        motivo = _get(row, "Motivo", "Reason")
        if motivo:
            notes = f"{motivo} - {notes}".strip(" -")
        expenses.append(
            {
                "vehicle_name": _get(row, "Nome do veículo", "Nome", "Vehicle"),
                "odometer": parse_decimal(
                    _get(row, "Odômetro (km)", "Odômetro km", "Odômetro", "Odometer")
                ),
                "occurred_at": parse_date(_get(row, "Data", "Date")),
                "amount": parse_decimal(
                    _get(row, "Valor total", "Valor", "Total", "Amount")
                ),
                "category_name": _get(
                    row, "Tipo de despesa", "Categoria", "Category", "Tipo"
                ),
                "vendor_name": _get(
                    row, "Local da despesa", "Local", "Vendor", "Local do serviço"
                ),
                "notes": notes,
            }
        )
    return expenses


# ---------------------------------------------------------------------------
# Legacy API
# ---------------------------------------------------------------------------


class DrivvoParser:
    """
    Parser for Drivvo CSV export files (legacy interface).

    Parses a Drivvo CSV file and returns a flat dict of row dicts grouped by
    section, plus an ``unsupported_sections`` list. This is the API used by the
    original parser and is kept for backward compatibility.
    """

    def __init__(
        self,
        delimiter: Optional[str] = None,
        encoding: Optional[str] = None,
    ) -> None:
        self.delimiter = delimiter
        self.encoding = encoding

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a Drivvo CSV file and group data by section.

        Returns:
            dict: Keys for each supported section ('vehicles', 'refuelings',
                  'expenses') with a list of row dicts, plus
                  'unsupported_sections'.
        """
        sections = parse_sections(
            file_path, encoding=self.encoding, delimiter=self.delimiter
        )
        result = {
            key: sections.get(key, {"headers": [], "rows": []})["rows"]
            for key in SUPPORTED_SECTIONS
        }
        result["unsupported_sections"] = sections.get("unsupported_sections", [])
        return result


def parse_drivvo_csv(file_path: str) -> Dict[str, Any]:
    """
    Parse a Drivvo CSV export file and group data by section.

    Convenience wrapper around :class:`DrivvoParser`.
    """
    return DrivvoParser().parse(file_path)
