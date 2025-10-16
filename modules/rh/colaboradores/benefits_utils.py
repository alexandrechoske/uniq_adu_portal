"""Utility helpers for handling collaborator benefits structures."""

from __future__ import annotations

import json
import re
import unicodedata
from copy import deepcopy
from typing import Any, Dict, Iterable, Tuple

# ----------------------------------------------------------------------------
# Benefit catalog and classification
# ----------------------------------------------------------------------------

BENEFICIOS_REGISTRY: Dict[str, Dict[str, str]] = {
    'ajuda_de_custo': {'label': 'Ajuda de Custo', 'categoria': 'remuneracao_adicional'},
    'auxilio_creche': {'label': 'Auxílio Creche', 'categoria': 'remuneracao_adicional'},
    'auxilio_moradia': {'label': 'Auxílio Moradia', 'categoria': 'remuneracao_adicional'},
    'auxilio_combustivel': {'label': 'Auxílio Combustível', 'categoria': 'remuneracao_adicional'},
    'auxilio_alimentacao': {'label': 'Auxílio Alimentação', 'categoria': 'remuneracao_adicional'},
    'bonus_resultados': {'label': 'Bônus de Resultados', 'categoria': 'remuneracao_adicional'},
    'gratificacao': {'label': 'Gratificação', 'categoria': 'remuneracao_adicional'},
    'vale_alimentacao': {'label': 'Vale Alimentação', 'categoria': 'beneficios_padrao'},
    'vale_refeicao': {'label': 'Vale Refeição', 'categoria': 'beneficios_padrao'},
    'vale_transporte': {'label': 'Vale Transporte', 'categoria': 'beneficios_padrao'},
    'vale_combustivel': {'label': 'Vale Combustível', 'categoria': 'beneficios_padrao'},
    'plano_saude': {'label': 'Plano de Saúde', 'categoria': 'beneficios_padrao'},
    'plano_odontologico': {'label': 'Plano Odontológico', 'categoria': 'beneficios_padrao'},
    'seguro_vida': {'label': 'Seguro de Vida', 'categoria': 'beneficios_padrao'},
    'auxilio_educacao': {'label': 'Auxílio Educação', 'categoria': 'beneficios_padrao'},
    'auxilio_internet': {'label': 'Auxílio Internet', 'categoria': 'beneficios_padrao'},
    'auxilio_energia': {'label': 'Auxílio Energia', 'categoria': 'beneficios_padrao'},
    'outros': {'label': 'Outro Benefício', 'categoria': 'beneficios_padrao'},
}

REMUNERACAO_SLUGS = {
    slug for slug, meta in BENEFICIOS_REGISTRY.items()
    if meta['categoria'] == 'remuneracao_adicional'
}
BENEFICIOS_PADRAO_SLUGS = {
    slug for slug, meta in BENEFICIOS_REGISTRY.items()
    if meta['categoria'] == 'beneficios_padrao'
}
BOOLEAN_LIKE_SLUGS = {'vale_transporte'}

BENEFICIOS_CATALOGO = [
    {'slug': slug, 'label': meta['label']}
    for slug, meta in BENEFICIOS_REGISTRY.items()
    if slug != 'outros'
]

# Preserve compatibility with legacy dropdown that expects "Outro Benefício" entry
BENEFICIOS_CATALOGO.append({'slug': 'outros', 'label': BENEFICIOS_REGISTRY['outros']['label']})

# ----------------------------------------------------------------------------
# Formatting helpers
# ----------------------------------------------------------------------------

def format_currency_br(value: Any) -> str:
    """Format numeric values using Brazilian currency formatting."""
    if value in (None, ''):
        return '-'

    try:
        amount = float(value)
    except (ValueError, TypeError):
        return '-'

    formatted = f"{amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {formatted}'


def normalize_decimal(value: Any) -> float | None:
    """Normalize inputs to float when possible."""
    if value in (None, ''):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        value_str = value.strip()
        if not value_str:
            return None
        value_str = value_str.replace('R$', '').replace(' ', '')
        value_str = value_str.replace('.', '').replace(',', '.')
        try:
            return float(value_str)
        except ValueError:
            return None

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def slugify_beneficio(nome: Any) -> str | None:
    """Convert benefit names to slug format."""
    if not nome:
        return None

    texto = unicodedata.normalize('NFKD', str(nome)).encode('ascii', 'ignore').decode('ascii')
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9]+', '_', texto)
    texto = texto.strip('_')
    return texto or None


def beneficio_label(slug: str) -> str:
    if not slug:
        return '-'
    meta = BENEFICIOS_REGISTRY.get(slug)
    if meta:
        return meta['label']
    partes = str(slug).split('_')
    return ' '.join(parte.capitalize() for parte in partes if parte)

# ----------------------------------------------------------------------------
# Core normalization logic
# ----------------------------------------------------------------------------

Structure = Dict[str, Dict[str, Any]]


def _empty_structure() -> Structure:
    return {'remuneracao_adicional': {}, 'beneficios_padrao': {}}


def _iter_raw_items(raw: Any) -> Iterable[Tuple[str, Any]]:
    if isinstance(raw, dict):
        return raw.items()
    if isinstance(raw, list):
        resultado = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            nome = (
                item.get('slug')
                or item.get('tipo')
                or item.get('codigo')
                or item.get('nome')
                or item.get('beneficio')
            )
            valor = item.get('valor')
            if nome is not None:
                resultado.append((nome, valor))
        return resultado
    return []


def _assign_value(structure: Structure, slug: str, valor: Any, categoria_forcada: str | None = None) -> None:
    if not slug:
        return

    categoria = categoria_forcada
    if not categoria:
        if slug in REMUNERACAO_SLUGS:
            categoria = 'remuneracao_adicional'
        else:
            categoria = 'beneficios_padrao'

    destino = structure.setdefault(categoria, {})

    if slug in BOOLEAN_LIKE_SLUGS and isinstance(valor, str):
        texto = valor.strip()
        if texto:
            destino[slug] = texto.capitalize()
        return

    valor_normalizado = normalize_decimal(valor)
    if valor_normalizado is None:
        if isinstance(valor, str) and valor.strip():
            destino[slug] = valor.strip()
        return

    destino[slug] = round(valor_normalizado, 2)


def normalize_beneficios(raw: Any) -> Structure:
    """Normalize benefits payload into the canonical nested structure."""
    if raw is None:
        return _empty_structure()

    if isinstance(raw, str):
        texto = raw.strip()
        if not texto:
            return _empty_structure()
        try:
            parsed = json.loads(texto)
        except json.JSONDecodeError:
            return _empty_structure()
        return normalize_beneficios(parsed)

    structure = _empty_structure()

    if isinstance(raw, dict) and (
        'remuneracao_adicional' in raw or 'beneficios_padrao' in raw
    ):
        for categoria in ('remuneracao_adicional', 'beneficios_padrao'):
            bloco = raw.get(categoria) or {}
            if not isinstance(bloco, dict):
                continue
            for slug_raw, valor in bloco.items():
                slug = slugify_beneficio(slug_raw)
                if slug:
                    _assign_value(structure, slug, valor, categoria_forcada=categoria)
        return structure

    for slug_raw, valor in _iter_raw_items(raw):
        slug = slugify_beneficio(slug_raw)
        if not slug:
            continue
        _assign_value(structure, slug, valor)

    return structure


def has_beneficios(estrutura: Any) -> bool:
    estrutura = normalize_beneficios(estrutura)
    return any(estrutura.get('remuneracao_adicional')) or any(estrutura.get('beneficios_padrao'))


def sum_beneficios_numeric(estrutura: Any) -> float:
    estrutura = normalize_beneficios(estrutura)
    total = 0.0
    for categoria in ('remuneracao_adicional', 'beneficios_padrao'):
        for valor in estrutura.get(categoria, {}).values():
            valor_num = normalize_decimal(valor)
            if valor_num is not None:
                total += valor_num
    return total


def build_beneficios_view(estrutura: Any) -> Dict[str, Any]:
    dados = normalize_beneficios(estrutura)
    view = {
        'remuneracao_adicional': {'items': [], 'total': 0.0, 'total_formatado': '-', 'has_items': False},
        'beneficios_padrao': {'items': [], 'total': 0.0, 'total_formatado': '-', 'has_items': False},
        'total_geral': 0.0,
        'total_geral_formatado': '-',
        'has_beneficios': False,
    }

    for categoria in ('remuneracao_adicional', 'beneficios_padrao'):
        itens = []
        total_categoria = 0.0
        for slug, valor in (dados.get(categoria) or {}).items():
            label = beneficio_label(slug)
            valor_num = normalize_decimal(valor)
            if valor_num is not None:
                total_categoria += valor_num
                valor_formatado = format_currency_br(valor_num)
                is_numeric = True
            else:
                valor_formatado = str(valor)
                is_numeric = False
            itens.append({
                'slug': slug,
                'label': label,
                'valor': valor_num if is_numeric else valor,
                'valor_formatado': valor_formatado,
                'is_numeric': is_numeric,
                'categoria': categoria,
            })

        itens.sort(key=lambda item: item['label'])
        view[categoria]['items'] = itens
        view[categoria]['total'] = round(total_categoria, 2) if itens else 0.0
        view[categoria]['total_formatado'] = (
            format_currency_br(total_categoria) if itens else 'R$ 0,00'
        )
        view[categoria]['has_items'] = bool(itens)

    total_geral = view['remuneracao_adicional']['total'] + view['beneficios_padrao']['total']
    view['total_geral'] = round(total_geral, 2)
    view['total_geral_formatado'] = format_currency_br(total_geral) if total_geral else 'R$ 0,00'
    view['has_beneficios'] = (
        view['remuneracao_adicional']['has_items'] or view['beneficios_padrao']['has_items']
    )

    return view


def merge_beneficios(base: Any, override: Any) -> Structure:
    """Merge two benefits structures, giving precedence to override values."""
    base_struct = normalize_beneficios(base)
    override_struct = normalize_beneficios(override)

    resultado = _empty_structure()
    for categoria in ('remuneracao_adicional', 'beneficios_padrao'):
        combinado = deepcopy(base_struct.get(categoria) or {})
        combinado.update(override_struct.get(categoria) or {})
        resultado[categoria] = combinado
    return resultado
