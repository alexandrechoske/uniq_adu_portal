import os, uuid, json, re, io, base64, threading
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, current_app, session
from routes.auth import login_required
from werkzeug.utils import secure_filename

# Dependências opcionais
try:
	from lexoid.api import parse as lexoid_parse
	LEXOID_AVAILABLE = True
except Exception:
	LEXOID_AVAILABLE = False

try:
	import google.generativeai as genai
	GEMINI_AVAILABLE = True
except Exception:
	GEMINI_AVAILABLE = False

UPLOAD_FOLDER = 'static/uploads/conferencia'
ALLOWED_EXTENSIONS = {'pdf'}

conferencia_bp = Blueprint(
	'conferencia', __name__,
	template_folder='templates',
	static_folder='static',
	# Ajuste static_url_path para evitar duplicação /conferencia/conferencia/static
	static_url_path='/conferencia_static',
	url_prefix='/conferencia'
)

SIMPLE_PROMPT = r"""Você é um extrator de INVOICE (comercial ou proforma). Analise o documento completo (todas as páginas) e retorne APENAS UM JSON ÚNICO e VÁLIDO seguindo exatamente a estrutura abaixo. Seja robusto a layouts variados, idiomas (PT/EN/DE/IT), tabelas em grade e UOMs não padronizadas (pce, pcs, kgs, mt, m, set).

REGRAS GERAIS
- Sempre retorne: valor_extraido (texto exato), *_norm (valor normalizado), confidence (0.50–0.99), page (int|null), source_snippet (texto curto que justifique).
- Normalizações:
	• Datas em *_norm = YYYY-MM-DD.
	• Números: remover milhar, trocar vírgula decimal por ponto (ex.: "1.198,50" -> 1198.50).
	• Moeda: currency_norm em ISO (USD, EUR, BRL...).
	• UOM: mapear para um conjunto canônico: PCS, KG, M, SET, BOX, N/A.
- Se o campo não existir, use null e registre em sumario.alertas (com breve motivo).
- Checagens cruzadas:
	• total_items_sum_norm = soma de itens com amount_norm != null (itens amount=0 permanecem, mas marcados).
	• Se houver TOTAL declarado, extraia invoice_total_declared_norm.
	• difference_norm = invoice_total_declared_norm - total_items_sum_norm quando ambos existirem.
	• Se |difference_norm| > 1% do total declarado, status = "alerta".
- Inferências:
	• country_of_acquisition: se ausente, inferir a partir do endereço do exportador (marcar inferido=true e why).
	• country_of_origin: aceitar múltiplos (por item), e no campo global consolidar como lista única (sem duplicatas); se vier “Germany, Austria”, registrar como array ["Germany","Austria"] em *_norm_arr.
- Itens especiais:
	• Se o item aparenta ser “documento/certificado/serviço” (ex.: "certificate 3.1", "inspection", "documentation"), classificar item_type="DOCUMENT" e permitir unit_price_norm/amount_norm=0 sem penalizar soma.
	• Se a descrição contiver quantidade alternativa (ex.: “36 Meter”) E a linha de qty usar outra UOM (ex.: “9,00 kgs”), preencher quantidade_alt com {valor_extraido, qty_alt_norm, uom_alt_norm}.
	• Campos regulatórios obrigatórios (marque alerta se faltarem): invoice_number, issue_date, incoterm, seller_exporter, buyer_consignee, gross_weight, net_weight, payment_terms, exporter_reference.

CAMPOS A EXTRAIR
{
	"sumario": {
		"status": "ok|alerta|erro",
		"total_erros_criticos": int,
		"total_observacoes": int,
		"total_alertas": int,
		"checks": {
			"total_items_sum_norm": number|null,
			"invoice_total_declared_norm": number|null,
			"difference_norm": number|null
		},
		"alertas": [string],
		"observacoes": [string],
		"conclusao": string
	},
	"campos": {
		"invoice_number": { "valor_extraido": string|null, "invoice_number_norm": string|null, "confidence": number, "page": int|null, "source_snippet": string },
		"issue_date": { "valor_extraido": string|null, "issue_date_norm": string|null, "confidence": number, "page": int|null, "source_snippet": string },
		"seller_exporter": { "valor_extraido": string|null, "confidence": number, "page": int|null, "source_snippet": string },
		"buyer_consignee": { "valor_extraido": string|null, "confidence": number, "page": int|null, "source_snippet": string },
		"exporter_reference": { "valor_extraido": string|null, "confidence": number, "page": int|null, "source_snippet": string },
		"payment_terms": { "valor_extraido": string|null, "confidence": number, "page": int|null, "source_snippet": string },
		"gross_weight": { "valor_extraido": string|null, "gross_weight_norm": number|null, "confidence": number, "page": int|null, "source_snippet": string },
		"net_weight": { "valor_extraido": string|null, "net_weight_norm": number|null, "confidence": number, "page": int|null, "source_snippet": string },
		"incoterm": { "valor_extraido": string|null, "incoterm_code_norm": string|null, "incoterm_place_norm": string|null, "confidence": number, "page": int|null, "source_snippet": string },
		"currency": { "valor_extraido": string|null, "currency_norm": string|null, "confidence": number },
		"country_of_origin": { "valor_extraido": string|null, "country_of_origin_norm_arr": [string]|null, "inferido": boolean, "why": string|null, "confidence": number },
		"country_of_acquisition": { "valor_extraido": string|null, "country_of_acquisition_norm": string|null, "inferido": boolean, "why": string|null, "confidence": number },
		"totais_detalhados": { "subtotal_norm": number|null, "freight_norm": number|null, "insurance_norm": number|null, "discount_norm": number|null, "taxes_norm": number|null, "grand_total_norm": number|null }
	},
	"itens_da_fatura": [ {
			"item_type": "PRODUCT|DOCUMENT|SERVICE",
			"descricao_completa": { "valor_extraido": string, "confidence": number, "page": int|null, "source_snippet": string },
			"hs_code": { "valor_extraido": string|null, "hs_code_norm": string|null, "confidence": number },
			"manufacturer": { "valor_extraido": string|null, "confidence": number },
			"country_of_origin_item": { "valor_extraido": string|null, "country_origin_item_norm": string|null, "confidence": number },
			"quantidade_unidade": { "valor_extraido": string|null, "qty_norm": number|null, "uom_norm": "PCS|KG|M|SET|BOX|N/A"|null, "confidence": number },
			"quantidade_alt": { "valor_extraido": string|null, "qty_alt_norm": number|null, "uom_alt_norm": "PCS|KG|M|SET|BOX|N/A"|null },
			"preco_unitario": { "valor_extraido": string|null, "unit_price_norm": number|null, "per": "UNIT|M|KG|SET|BOX|N/A"|null, "confidence": number },
			"valor_total_item": { "valor_extraido": string|null, "amount_norm": number|null, "confidence": number }
	} ]
}

INSTRUÇÕES DE BUSCA (resumido)
- invoice_number: padrões "Invoice", "Rechnung", "Fattura", etc. Remover prefixos e normalizar.
- incoterm: separar code/place (FCA Bremen).
- pesos (gross_weight/net_weight): normalizar para número (kg). Se outra unidade (lbs) converter se possível ou retornar valor bruto.
- payment_terms: extrair texto curto (ex.: "30 days", "ADVANCE 50% / 50% before shipment").
- exporter_reference: localizar referências do exportador (ex.: "Ref:" / "Our Ref.").
- country lists: separar por vírgulas ou conjunções.
- Totais detalhados: mapear linhas que contenham Subtotal/Freight/Insurance/Discount/Tax/VAT/Grand Total.

Retorne APENAS o JSON final, sem comentários ou texto adicional.
"""

def ensure_upload_folder():
	os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename: str) -> bool:
	return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_google_key():
	"""Garante que GOOGLE_API_KEY esteja definido para libs que esperam esse nome.
	Se já existir, não altera. Caso contrário tenta usar GEMINI_API_KEY.
	"""
	if not os.getenv('GOOGLE_API_KEY'):
		gem = os.getenv('GEMINI_API_KEY')
		if gem:
			os.environ['GOOGLE_API_KEY'] = gem
			try:
				current_app.logger.info('[SIMPLE] GOOGLE_API_KEY mapeado a partir de GEMINI_API_KEY')
			except Exception:
				pass

def safe_parse_json(raw: str):
	if not raw:
		return None
	if '```' in raw:
		m = re.search(r'```json\s*(.*?)```', raw, re.DOTALL|re.IGNORECASE)
		if m:
			raw = m.group(1)
	start = raw.find('{')
	end = raw.rfind('}')
	if start != -1 and end != -1 and end > start:
		snippet = raw[start:end+1]
		try:
			return json.loads(snippet)
		except Exception:
			pass
	try:
		return json.loads(raw)
	except Exception:
		return None

@conferencia_bp.route('/')
@login_required
def index():
	return render_template('conferencia.html')

@conferencia_bp.route('/simple')
@login_required
def simple_page():
	return render_template('conferencia.html')

@conferencia_bp.route('/simple/analyze', methods=['POST'])
@login_required
def simple_analyze():
	if not LEXOID_AVAILABLE:
		return jsonify({'success': False, 'error': 'Lexoid não instalado'}), 500
	if 'file' not in request.files:
		return jsonify({'success': False, 'error': 'Arquivo não enviado'}), 400
	f = request.files['file']
	if f.filename == '' or not allowed_file(f.filename):
		return jsonify({'success': False, 'error': 'Envie um PDF .pdf'}), 400
	ensure_upload_folder()
	filename = secure_filename(f.filename)
	saved_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{filename}"
	path = os.path.join(UPLOAD_FOLDER, saved_name)
	f.save(path)
	start = datetime.now()
	current_app.logger.info(f"[SIMPLE] Arquivo salvo {path}")
	# Garante chave esperada pelo Lexoid
	ensure_google_key()
	md = None
	parse_mode = None
	try:
		try:
			md = lexoid_parse(path, parser_type='LLM_PARSE').get('raw')
			parse_mode = 'LLM_PARSE'
		except Exception:
			md = lexoid_parse(path, parser_type='STATIC_PARSE').get('raw')
			parse_mode = 'STATIC_PARSE'
	except Exception as e:
		return jsonify({'success': False, 'error': f'Falha Lexoid: {e}'}), 500
	if not md:
		return jsonify({'success': False, 'error': 'Retorno vazio do Lexoid'}), 500

	md_trunc = md[:45000]
	palavras = len(re.findall(r'\w+', md_trunc))
	paginas = md_trunc.count('\n\n')//40 + 1  # heurística simples

	llm_json = None
	llm_error = None
	api_key = os.getenv('GEMINI_API_KEY')
	if api_key and GEMINI_AVAILABLE:
		try:
			genai.configure(api_key=api_key)
			model = genai.GenerativeModel(os.getenv('GEMINI_MODEL','gemini-1.5-flash'))
			prompt = SIMPLE_PROMPT + "\n\nMARKDOWN_INICIO\n" + md_trunc + "\nMARKDOWN_FIM"
			resp = model.generate_content([{ 'text': prompt }])
			llm_json = safe_parse_json(resp.text)
			if not isinstance(llm_json, dict):
				llm_error = 'Falha ao parsear JSON'
		except Exception as e:
			llm_error = str(e)
	else:
		llm_error = 'GEMINI_API_KEY ausente ou lib indisponível'

	elapsed_ms = int((datetime.now() - start).total_seconds()*1000)
	return jsonify({
		'success': True,
		'file': filename,
		'saved_name': saved_name,
		'elapsed_ms': elapsed_ms,
		'lexoid_mode': parse_mode,
		'markdown_preview': md_trunc[:1200],
		'palavras': palavras,
		'paginas_estimado': paginas,
		'json': enrich_full_invoice_json(md_trunc, llm_json),
		'llm_error': llm_error
	})

# (Opcional) endpoint de saúde
@conferencia_bp.route('/simple/health')
def simple_health():
	return jsonify({
		'lexoid': LEXOID_AVAILABLE,
		'gemini': GEMINI_AVAILABLE,
		'has_key': bool(os.getenv('GEMINI_API_KEY'))
	})

@conferencia_bp.route('/static-test')
@login_required
def static_test():
	css_rel = 'css/simple.css'
	js_rel = 'js/simple.js'
	css_path = os.path.join(conferencia_bp.static_folder, css_rel)
	js_path = os.path.join(conferencia_bp.static_folder, js_rel)
	return jsonify({
		'static_folder': conferencia_bp.static_folder,
		'css_exists': os.path.exists(css_path),
		'js_exists': os.path.exists(js_path),
		'css_path': css_path,
		'js_path': js_path
	})

# ================= ENRIQUECIMENTO PÓS-PROCESSO ==================

def enrich_full_invoice_json(markdown_text: str, data: dict | None) -> dict | None:
	"""Garante estrutura completa conforme especificação, preenchendo defaults e calculando verificações."""
	if data is None:
		return None
	# Se já parece completo (tem 'campos' e 'itens_da_fatura') apenas pós-processa
	if 'campos' not in data or 'itens_da_fatura' not in data:
		# Converter de formato simples (campos_chave / possiveis_itens)
		data = convert_simple_to_full(markdown_text, data)
	return post_process_full(markdown_text, data)

def convert_simple_to_full(markdown_text: str, data: dict) -> dict:
	campos_chave = data.get('campos_chave', {})
	itens = data.get('possiveis_itens', []) or []
	def wrap_field(valor, norm_key=None):
		base = {
			'valor_extraido': valor,
			'confidence': 0.75 if valor else 0.0,
			'page': 1 if valor else None,
			'source_snippet': find_snippet(markdown_text, valor) if valor else ''
		}
		if norm_key:
			base[norm_key] = normalize_generic(norm_key, valor)
		return base
	campos = {
		'invoice_number': wrap_field(campos_chave.get('invoice_number'), 'invoice_number_norm'),
		'issue_date': wrap_field(campos_chave.get('issue_date'), 'issue_date_norm'),
		'seller_exporter': wrap_field(None),
		'buyer_consignee': wrap_field(None),
		'incoterm': wrap_field(campos_chave.get('incoterm')),
		'currency': { 'valor_extraido': campos_chave.get('currency'), 'currency_norm': normalize_currency(campos_chave.get('currency')), 'confidence': 0.7 if campos_chave.get('currency') else 0.0 },
		'country_of_origin': { 'valor_extraido': None, 'inferido': False, 'confidence': 0.0 },
		'country_of_acquisition': { 'valor_extraido': None, 'inferido': False, 'confidence': 0.0 }
	}
	itens_norm = []
	for it in itens:
		desc = it.get('descricao')
		qtd = it.get('quantidade')
		preco = it.get('preco_unitario')
		total = it.get('valor_total')
		itens_norm.append({
			'descricao_completa': {
				'valor_extraido': desc,
				'confidence': 0.75 if desc else 0.0,
				'page': 1,
				'source_snippet': find_snippet(markdown_text, desc) if desc else ''
			},
			'quantidade_unidade': {
				'valor_extraido': qtd,
				'qty_norm': parse_number(qtd),
				'unit_norm': infer_unit(qtd),
				'confidence': 0.7 if qtd else 0.0
			},
			'preco_unitario': {
				'valor_extraido': preco,
				'unit_price_norm': parse_number(preco),
				'per': None,
				'confidence': 0.7 if preco else 0.0
			},
			'valor_total_item': {
				'valor_extraido': total,
				'amount_norm': parse_number(total),
				'confidence': 0.7 if total else 0.0
			}
		})
	sumario = data.get('sumario', {})
	if 'status' not in sumario:
		sumario = {'status': 'ok', 'total_erros_criticos': 0, 'total_observacoes': 0, 'total_alertas': 0, 'checks': {}, 'conclusao': ''}
	return { 'sumario': sumario, 'campos': campos, 'itens_da_fatura': itens_norm }

def post_process_full(markdown_text: str, data: dict) -> dict:
	campos = data.setdefault('campos', {})
	itens = data.setdefault('itens_da_fatura', [])
	sumario = data.setdefault('sumario', {})
	# Normalizações adicionais
	inv_field = campos.get('invoice_number', {})
	if inv_field.get('valor_extraido') and 'invoice_number_norm' not in inv_field:
		inv_field['invoice_number_norm'] = normalize_invoice_number(inv_field.get('valor_extraido'))
	date_field = campos.get('issue_date', {})
	if date_field.get('valor_extraido') and 'issue_date_norm' not in date_field:
		date_field['issue_date_norm'] = normalize_date(date_field.get('valor_extraido'))
	currency_field = campos.get('currency', {})
	if currency_field.get('valor_extraido') and 'currency_norm' not in currency_field:
		currency_field['currency_norm'] = normalize_currency(currency_field.get('valor_extraido'))

	# Totais
	total_items = 0.0
	for it in itens:
		amt = it.get('valor_total_item', {}).get('amount_norm')
		if amt is None:
			# tentar parse
			raw = it.get('valor_total_item', {}).get('valor_extraido')
			parsed = parse_number(raw)
			it['valor_total_item']['amount_norm'] = parsed
			amt = parsed
		if isinstance(amt, (int, float)):
			total_items += amt
	# Procurar total declarado
	declared = find_declared_total(markdown_text)
	checks = {
		'total_items_sum_norm': round(total_items, 2) if total_items else None,
		'invoice_total_declared_norm': declared,
		'difference_norm': round(declared - total_items, 2) if (declared is not None and total_items) else None
	}
	sumario['checks'] = checks
	# Erros críticos
	inc = campos.get('incoterm', {})
	if not inc.get('valor_extraido'):
		sumario['status'] = 'alerta'
		sumario['total_erros_criticos'] = sumario.get('total_erros_criticos', 0) + 1
		sumario['conclusao'] = (sumario.get('conclusao','') + ' | Incoterm ausente').strip(' |')
	# Alertas contagem
	sumario['total_alertas'] = sumario.get('total_alertas') or sumario.get('total_erros_criticos', 0)
	# Observações
	sumario.setdefault('total_observacoes', 0)
	return data

# ================= FUNÇÕES AUXILIARES ==================

def normalize_generic(kind: str, value: str | None):
	if value is None:
		return None
	if kind == 'issue_date_norm':
		return normalize_date(value)
	if kind == 'invoice_number_norm':
		return normalize_invoice_number(value)
	return value

def normalize_invoice_number(raw: str | None):
	if not raw:
		return None
	r = raw.upper()
	r = re.sub(r'INVOICE\s*NO\.?\s*[:#]?','', r)
	r = re.sub(r'\b(PI|INV|FE|NO|Nº|#)\s*','', r)
	r = re.sub(r'[^A-Z0-9./-]','', r)
	# Se múltiplos (separados por vírgula) manter primeiro
	if ',' in r:
		r = r.split(',')[0]
	return r.strip()[:40] or None

def normalize_date(raw: str | None):
	if not raw:
		return None
	raw = raw.strip()
	# Formatos comuns
	try:
		from datetime import datetime as _dt
		for fmt in ('%Y-%m-%d','%d-%b-%Y','%d-%b-%y','%d/%m/%Y','%d-%m-%Y','%d/%m/%y'):
			try:
				dt = _dt.strptime(raw, fmt)
				return dt.strftime('%Y-%m-%d')
			except Exception:
				continue
	except Exception:
		pass
	# Heurística: extrair yyyy-mm-dd pattern
	m = re.search(r'(20\d{2})[-/](\d{2})[-/](\d{2})', raw)
	if m:
		return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
	return None

def normalize_currency(raw: str | None):
	if not raw:
		return None
	r = raw.upper().replace('US$','USD').replace('$','USD')
	if r in ('USD','EUR','BRL','GBP','CNY','JPY'): return r
	if 'EU' in r: return 'EUR'
	if 'R$' in r or 'BR' in r: return 'BRL'
	return r[:3]

def parse_number(raw: str | None):
	if not raw:
		return None
	txt = raw.replace(' ','')
	# Remove currency symbols
	txt = re.sub(r'[A-Z$€£R$]','', txt)
	# Troca separadores
	if re.match(r'^\d{1,3}(,\d{3})+\.\d{2}$', txt):
		txt = txt.replace(',','')
	elif re.match(r'^\d{1,3}(\.\d{3})+,\d{2}$', txt):
		txt = txt.replace('.','').replace(',', '.')
	elif txt.count(',')==1 and txt.count('.')==0:
		txt = txt.replace(',', '.')
	txt = re.sub(r'[^0-9.\-]','', txt)
	try:
		return float(txt)
	except Exception:
		return None

def infer_unit(raw: str | None):
	if not raw: return None
	m = re.search(r'\b(PCS|KG|KGS|MT|TON|UN|SETS|M|LTR|LTS)\b', raw.upper())
	return (m.group(1) if m else None)

def find_snippet(markdown_text: str, value: str | None):
	if not value:
		return ''
	val = value.strip()
	idx = markdown_text.find(val[:30])
	if idx == -1:
		return ''
	start = max(0, idx-40)
	end = min(len(markdown_text), idx+80)
	return markdown_text[start:end].replace('\n',' ')[:140]

def find_declared_total(markdown_text: str):
	# Busca linha com TOTAL / AMOUNT e número
	pattern = re.compile(r'(?i)(TOTAL\s*(AMOUNT)?)[^0-9]{0,15}([0-9.,]+)')
	candidates = []
	for m in pattern.finditer(markdown_text):
		val = parse_number(m.group(3))
		if val:
			candidates.append(val)
	if candidates:
		# maior valor costuma ser total
		return round(max(candidates),2)
	return None
