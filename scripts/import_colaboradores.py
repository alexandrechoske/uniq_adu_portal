"""Import collaborators from the RH spreadsheet into Supabase."""
from __future__ import annotations

import argparse
import json
import os
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv
from supabase import Client, create_client


@dataclass
class RowData:
    index: int
    nome: str
    status: str
    matricula: Optional[str]
    cpf: str
    cpf_digits: str
    data_nascimento: Optional[str]
    data_admissao: Optional[str]
    data_demissao: Optional[str]
    data_reajuste: Optional[str]
    data_exame_periodico: Optional[str]
    genero: Optional[str]
    escolaridade: Optional[str]
    pis: Optional[str]
    departamento: Optional[str]
    cargo_inicial: Optional[str]
    cargo_atual: Optional[str]
    salario_inicial: Optional[float]
    salario_atual: Optional[float]


@dataclass
class PreparedData:
    rows: List[RowData]
    departamentos: Dict[str, str]
    cargos: Dict[str, Tuple[str, Optional[str]]]
    duplicates: Dict[str, List[RowData]] = field(default_factory=dict)


STATUS_MAP = {
    "ATIVO": "Ativo",
    "INATIVO": "Inativo",
}


GENDER_MAP = {
    "MASCULINO": "MASCULINO",
    "FEMININO": "FEMININO",
    "NAO INFORMADO": "PREFIRO NAO INFORMAR",
    "NAO-BINARIO": "NAO-BINARIO",
    "NAO BINARIO": "NAO-BINARIO",
}


def canonical_key(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = (value or "").strip()
    normalized = " ".join(normalized.split())
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = (
        "".join(
            ch
            for ch in normalized.lower()
            if ch.isalnum() or ch.isspace()
        )
    )
    return " ".join(normalized.split()) or None


def clean_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "nat"}:
        return None
    return " ".join(text.split())


def sanitize_digits(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits or None


def format_cpf(value: Optional[str]) -> Optional[str]:
    digits = sanitize_digits(value)
    if not digits:
        return None
    if len(digits) != 11:
        return digits
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def parse_date(value) -> Optional[str]:
    if value is None:
        return None
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, float)):
        try:
            return pd.to_datetime(value, origin="1899-12-30", unit="D").date().isoformat()
        except Exception:
            return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    try:
        return pd.to_datetime(text).date().isoformat()
    except Exception:
        return None


def parse_currency(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    cleaned = (
        text.replace("R$", "")
        .replace(" ", "")
        .replace(".", "")
        .replace(",", ".")
    )
    if cleaned.lower() in {"", "nan", "none", "null"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    column_map = {}
    for original in df.columns:
        key = canonical_key(original)
        if key:
            column_map[original] = key.replace(" ", "_")
    df = df.rename(columns=column_map)
    return df


def load_dataframe(path: Path) -> PreparedData:
    df = pd.read_excel(path)
    df = normalize_columns(df)

    required_columns = {
        "nome",
        "status",
        "cpf",
        "data_de_nasc",
        "admissao",
        "departamento",
        "cargo_inicial",
        "cargo_atual",
    }
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Missing expected columns: {', '.join(sorted(missing))}")

    rows: List[RowData] = []
    departamentos: Dict[str, str] = {}
    cargos: Dict[str, Tuple[str, Optional[str]]] = {}
    duplicates: Dict[str, List[RowData]] = defaultdict(list)

    for idx, record in df.iterrows():
        nome = clean_string(record.get("nome"))
        if not nome:
            continue

        raw_cpf = record.get("cpf")
        cpf_fmt = format_cpf(raw_cpf)
        cpf_digits = sanitize_digits(raw_cpf)

        status_raw = clean_string(record.get("status"))
        status_key = status_raw.upper() if status_raw else ""
        status = STATUS_MAP.get(status_key)
        if not status:
            if status_raw is None and not cpf_digits and clean_string(record.get("departamento")) is None:
                continue
            raise ValueError(f"Unknown status '{status_raw}' for row {idx}")

        if not cpf_digits:
            raise ValueError(f"Missing CPF for row {idx} ({nome})")

        row = RowData(
            index=idx,
            nome=nome,
            status=status,
            matricula=clean_string(record.get("matricula")) or None,
            cpf=cpf_fmt or cpf_digits,
            cpf_digits=cpf_digits,
            data_nascimento=parse_date(record.get("data_de_nasc")),
            data_admissao=parse_date(record.get("admissao")),
            data_demissao=parse_date(record.get("demissao")),
            data_reajuste=parse_date(record.get("reajuste")),
            data_exame_periodico=parse_date(record.get("exame_periodico_realizado")),
            genero=_map_genero(clean_string(record.get("genero"))),
            escolaridade=clean_string(record.get("escolaridade")),
            pis=sanitize_digits(record.get("pis")),
            departamento=clean_string(record.get("departamento")),
            cargo_inicial=clean_string(record.get("cargo_inicial")),
            cargo_atual=clean_string(record.get("cargo_atual")),
            salario_inicial=parse_currency(record.get("salario_inicial")),
            salario_atual=parse_currency(record.get("salario_atual")),
        )

        if not row.data_admissao:
            raise ValueError(f"Missing admission date for row {idx} ({nome})")
        if not row.departamento:
            raise ValueError(f"Missing department for row {idx} ({nome})")
        if not row.cargo_inicial:
            raise ValueError(f"Missing initial role for row {idx} ({nome})")
        if not row.cargo_atual:
            row.cargo_atual = row.cargo_inicial

        dep_key = canonical_key(row.departamento)
        if dep_key:
            departamentos.setdefault(dep_key, row.departamento)

        cargo_initial_key = canonical_key(row.cargo_inicial)
        if cargo_initial_key:
            cargos.setdefault(cargo_initial_key, (row.cargo_inicial, infer_grupo_cargo(row.cargo_inicial)))

        cargo_current_key = canonical_key(row.cargo_atual)
        if cargo_current_key:
            cargos.setdefault(cargo_current_key, (row.cargo_atual, infer_grupo_cargo(row.cargo_atual)))

        rows.append(row)
        duplicates[row.cpf_digits].append(row)

    duplicates = {cpf: recs for cpf, recs in duplicates.items() if len(recs) > 1}
    return PreparedData(rows=rows, departamentos=departamentos, cargos=cargos, duplicates=duplicates)


def _map_genero(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    upper = value.upper()
    return GENDER_MAP.get(upper, upper)


def infer_grupo_cargo(nome: str) -> str:
    texto = nome.lower()
    if any(word in texto for word in ["diretor", "ceo", "presidente"]):
        return "Estrat\u00e9gico"
    if any(word in texto for word in ["coordenador", "coordenadora", "lider", "l\u00edder", "gerente"]):
        return "Lideran\u00e7a"
    if any(word in texto for word in ["administrativo", "finance", "gestao", "gest\u00e3o", "rh", "marketing"]):
        return "Administrativo"
    if any(word in texto for word in ["aprendiz", "estagi", "est\u00e1gio"]):
        return "Operacional"
    if any(word in texto for word in ["comercio exterior", "com\u00e9rcio exterior", "import", "export"]):
        return "Operacional"
    return "Operacional"


def ensure_departamentos(client: Client, prepared: PreparedData, dry_run: bool) -> Dict[str, Dict[str, str]]:
    response = client.table("rh_departamentos").select("id, nome_departamento").execute()
    existing = response.data or []
    lookup: Dict[str, Dict[str, str]] = {}
    for item in existing:
        key = canonical_key(item["nome_departamento"])
        if key:
            lookup[key] = item

    novos = []
    for key, nome in prepared.departamentos.items():
        if key not in lookup:
            novos.append({"nome_departamento": nome})

    if novos and not dry_run:
        client.table("rh_departamentos").upsert(novos, on_conflict="nome_departamento").execute()
        response = client.table("rh_departamentos").select("id, nome_departamento").execute()
        existing = response.data or []
        lookup = {canonical_key(item["nome_departamento"]): item for item in existing if canonical_key(item["nome_departamento"]) }

    return lookup


def ensure_cargos(client: Client, prepared: PreparedData, dry_run: bool) -> Dict[str, Dict[str, str]]:
    response = client.table("rh_cargos").select("id, nome_cargo, grupo_cargo").execute()
    existing = response.data or []
    lookup: Dict[str, Dict[str, str]] = {}
    for item in existing:
        key = canonical_key(item["nome_cargo"])
        if key:
            lookup[key] = item

    novos = []
    for key, (nome, grupo) in prepared.cargos.items():
        if key not in lookup:
            novos.append({"nome_cargo": nome, "grupo_cargo": grupo})

    if novos and not dry_run:
        client.table("rh_cargos").upsert(novos, on_conflict="nome_cargo").execute()
        response = client.table("rh_cargos").select("id, nome_cargo, grupo_cargo").execute()
        existing = response.data or []
        lookup = {canonical_key(item["nome_cargo"]): item for item in existing if canonical_key(item["nome_cargo"]) }

    return lookup


def group_rows_by_cpf(prepared: PreparedData) -> Dict[str, List[RowData]]:
    grouped: Dict[str, List[RowData]] = defaultdict(list)
    for row in prepared.rows:
        grouped[row.cpf_digits].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda item: item.data_admissao or "")
    return grouped


def create_colaborador_payload(row: RowData, for_update: bool = False) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "nome_completo": row.nome,
        "cpf": row.cpf,
        "data_nascimento": row.data_nascimento,
        "data_admissao": row.data_admissao,
        "status": row.status,
    }

    optional_fields = {
        "matricula": row.matricula,
        "genero": row.genero,
        "escolaridade": row.escolaridade,
        "pis_pasep": row.pis,
    }
    for column, value in optional_fields.items():
        if value is not None:
            payload[column] = value
        elif for_update:
            payload[column] = None

    if row.status == "Inativo" and row.data_demissao:
        payload["data_desligamento"] = row.data_demissao
    elif for_update:
        payload["data_desligamento"] = None

    return payload


def build_historico_entries(
    colaborador_id: str,
    rows: Iterable[RowData],
    departamento_lookup: Dict[str, Dict[str, str]],
    cargo_lookup: Dict[str, Dict[str, str]],
) -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    for row in rows:
        departamento_id = resolve_lookup_id(departamento_lookup, row.departamento, "departamento")
        cargo_admissao_id = resolve_lookup_id(cargo_lookup, row.cargo_inicial, "cargo inicial")
        cargo_atual_id = resolve_lookup_id(cargo_lookup, row.cargo_atual, "cargo atual")

        admissao_entry = {
            "colaborador_id": colaborador_id,
            "tipo_evento": "Admiss\u00e3o",
            "data_evento": row.data_admissao,
            "departamento_id": departamento_id,
            "cargo_id": cargo_admissao_id,
            "salario_mensal": row.salario_inicial,
            "descricao_e_motivos": "Migra\u00e7\u00e3o: admiss\u00e3o registrada no legado",
            "status_contabilidade": "Pendente",
        }
        entries.append(admissao_entry)

        needs_structural = (
            row.cargo_atual and row.cargo_inicial and canonical_key(row.cargo_atual) != canonical_key(row.cargo_inicial)
        ) or (
            row.salario_atual is not None and row.salario_inicial is not None and abs(row.salario_atual - row.salario_inicial) > 0.01
        )

        if needs_structural:
            data_evento = row.data_reajuste or row.data_demissao or datetime.now().date().isoformat()
            estrutural_entry = {
                "colaborador_id": colaborador_id,
                "tipo_evento": "Altera\u00e7\u00e3o Estrutural",
                "data_evento": data_evento,
                "departamento_id": departamento_id,
                "cargo_id": cargo_atual_id,
                "salario_mensal": row.salario_atual,
                "descricao_e_motivos": "Migra\u00e7\u00e3o: atualiza\u00e7\u00e3o de cargo/sal\u00e1rio",
                "status_contabilidade": "Pendente",
            }
            entries.append(estrutural_entry)

        if row.status == "Inativo" and row.data_demissao:
            demissao_entry = {
                "colaborador_id": colaborador_id,
                "tipo_evento": "Demiss\u00e3o",
                "data_evento": row.data_demissao,
                "descricao_e_motivos": "Migra\u00e7\u00e3o: desligamento registrado no legado",
                "status_contabilidade": "Pendente",
            }
            entries.append(demissao_entry)
    return entries


def sync_historico_entries(
    client: Client,
    colaborador_id: str,
    entries: List[Dict[str, object]],
) -> None:
    if not entries:
        return
    response = (
        client.table("rh_historico_colaborador")
        .select("id, tipo_evento, data_evento")
        .eq("colaborador_id", colaborador_id)
        .execute()
    )
    existing = {
        (item["tipo_evento"], item["data_evento"]): item["id"]
        for item in (response.data or [])
    }
    for entry in entries:
        key = (entry["tipo_evento"], entry["data_evento"])
        payload = entry.copy()
        payload.pop("colaborador_id", None)
        if key in existing:
            client.table("rh_historico_colaborador").update(payload).eq("id", existing[key]).execute()
        else:
            client.table("rh_historico_colaborador").insert(entry).execute()


def sync_exame_event(
    client: Client,
    colaborador_id: str,
    event: Optional[Dict[str, object]],
) -> None:
    if not event:
        return
    response = (
        client.table("rh_eventos_colaborador")
        .select("id, data_inicio")
        .eq("colaborador_id", colaborador_id)
        .eq("tipo_evento", "Exame Peri\u00f3dico")
        .execute()
    )
    existing = response.data or []
    match = next((item for item in existing if item.get("data_inicio") == event["data_inicio"]), None)
    payload = event.copy()
    payload.pop("colaborador_id", None)
    if match:
        client.table("rh_eventos_colaborador").update(payload).eq("id", match["id"]).execute()
    else:
        client.table("rh_eventos_colaborador").insert(event).execute()


def resolve_lookup_id(lookup: Dict[str, Dict[str, str]], value: Optional[str], label: str) -> Optional[str]:
    if not value:
        return None
    key = canonical_key(value)
    if not key:
        return None
    if key not in lookup:
        raise ValueError(f"Valor '{value}' nao encontrado para {label}")
    return lookup[key]["id"]


def maybe_create_exame_event(colaborador_id: str, row: RowData) -> Optional[Dict[str, object]]:
    if not row.data_exame_periodico:
        return None
    return {
        "colaborador_id": colaborador_id,
        "tipo_evento": "Exame Peri\u00f3dico",
        "data_inicio": row.data_exame_periodico,
        "status": "Realizado",
        "descricao": "Migra\u00e7\u00e3o: exame peri\u00f3dico do legado",
    }


def run_import(client: Client, prepared: PreparedData, dry_run: bool) -> Dict[str, object]:
    departamento_lookup = ensure_departamentos(client, prepared, dry_run)
    cargo_lookup = ensure_cargos(client, prepared, dry_run)

    grouped = group_rows_by_cpf(prepared)
    total = len(grouped)
    processed = 0
    created = 0
    updated = 0
    failures: List[Tuple[str, str]] = []

    if dry_run:
        summary = {
            "total_registros_planilha": len(prepared.rows),
            "colaboradores_unicos": total,
            "departamentos_novos": [name for key, name in prepared.departamentos.items() if key not in departamento_lookup],
            "cargos_novos": [name for key, (name, _) in prepared.cargos.items() if key not in cargo_lookup],
            "duplicados_por_cpf": {cpf: [r.index for r in rows] for cpf, rows in prepared.duplicates.items()},
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return summary

    for _, rows in grouped.items():
        rows_sorted = sorted(rows, key=lambda r: r.data_admissao or "")
        master = rows_sorted[-1]
        payload_insert = create_colaborador_payload(master)
        payload_update = create_colaborador_payload(master, for_update=True)
        created_new = False
        colaborador_id: Optional[str] = None
        try:
            existing = (
                client.table("rh_colaboradores")
                .select("id")
                .eq("cpf", master.cpf)
                .execute()
            )
            if existing.data:
                colaborador_id = existing.data[0]["id"]
                client.table("rh_colaboradores").update(payload_update).eq("id", colaborador_id).execute()
                updated += 1
            else:
                response = client.table("rh_colaboradores").insert(payload_insert).execute()
                if not response.data:
                    raise RuntimeError("Insert returned no data")
                colaborador_id = response.data[0]["id"]
                created += 1
                created_new = True

            historicos = build_historico_entries(colaborador_id, rows_sorted, departamento_lookup, cargo_lookup)
            sync_historico_entries(client, colaborador_id, historicos)

            exame_evento = maybe_create_exame_event(colaborador_id, master)
            sync_exame_event(client, colaborador_id, exame_evento)
            processed += 1
        except Exception as exc:  # pragma: no cover
            failures.append((master.nome, str(exc)))
            if created_new and colaborador_id:
                client.table("rh_colaboradores").delete().eq("id", colaborador_id).execute()

    print(
        f"Processados: {processed}/{total} | Criados: {created} | Atualizados: {updated} | Falhas: {len(failures)}"
    )
    if failures:
        for nome, motivo in failures:
            print(f"[ERRO] {nome}: {motivo}")
    return {
        "processados": processed,
        "criados": created,
        "atualizados": updated,
        "falhas": failures,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Importa colaboradores para o Supabase")
    parser.add_argument("--path", required=True, help="Caminho do arquivo Excel")
    parser.add_argument("--dry-run", action="store_true", help="Executa apenas validacoes sem inserir dados")
    return parser


def main() -> None:
    load_dotenv()
    parser = build_argument_parser()
    args = parser.parse_args()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not supabase_url or not supabase_key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_KEY precisam estar configurados no ambiente")

    client = create_client(supabase_url, supabase_key)
    data_path = Path(args.path)
    if not data_path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {data_path}")

    prepared = load_dataframe(data_path)
    run_import(client, prepared, args.dry_run)


if __name__ == "__main__":
    main()
