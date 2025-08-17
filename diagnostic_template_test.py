"""
Script de diagnóstico para testar renderização de templates do Analytics
"""

from flask import Flask, render_template, render_template_string
import os

# Criar uma aplicação Flask simples para teste
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-key'

# Configurar o diretório de templates
analytics_templates = os.path.join(
    os.path.dirname(__file__), 
    'modules', 'analytics', 'templates'
)

# Adicionar o diretório de templates do analytics
app.jinja_loader.searchpath.append(analytics_templates)

@app.route('/test-analytics-agente')
def test_analytics_agente():
    """Teste básico do template analytics_agente.html"""
    try:
        # Tentar renderizar o template original
        result = render_template('analytics_agente.html', analytics_type='agente')
        return f"<h1>SUCCESS</h1><p>Template renderizado com sucesso!</p><p>Tamanho: {len(result)} caracteres</p><hr>{result[:500]}..."
    except Exception as e:
        return f"<h1>ERROR</h1><p>Erro ao renderizar template: {str(e)}</p>"

@app.route('/test-base-template')
def test_base_template():
    """Teste do template base.html"""
    try:
        # Usar o caminho correto para base.html (no diretório templates raiz)
        base_path = os.path.join(os.path.dirname(__file__), 'templates')
        app.jinja_loader.searchpath.insert(0, base_path)
        
        result = render_template('base.html')
        return f"<h1>SUCCESS</h1><p>Template base renderizado com sucesso!</p><p>Tamanho: {len(result)} caracteres</p>"
    except Exception as e:
        return f"<h1>ERROR</h1><p>Erro ao renderizar template base: {str(e)}</p>"

@app.route('/test-simple')
def test_simple():
    """Teste com um template simples inline"""
    template_str = '''
    <!DOCTYPE html>
    <html>
    <head><title>Teste Simples</title></head>
    <body>
        <h1>Template Simples Funcionando!</h1>
        <p>Tipo de analytics: {{ analytics_type }}</p>
    </body>
    </html>
    '''
    return render_template_string(template_str, analytics_type='teste')

if __name__ == '__main__':
    print("Iniciando servidor de diagnóstico...")
    print("Diretórios de templates:")
    print(f"- Analytics: {analytics_templates}")
    print(f"- Base: {os.path.join(os.path.dirname(__file__), 'templates')}")
    
    app.run(debug=True, port=5001)
