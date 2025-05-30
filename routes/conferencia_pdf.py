from flask import Blueprint, render_template, request, jsonify, session, url_for, send_file
import os
import PyPDF2
from PIL import Image, ImageDraw, ImageFont
from pdf2image import convert_from_path
from routes.auth import login_required, role_required
import tempfile
import uuid
import io
from extensions import supabase

bp = Blueprint('conferencia_pdf', __name__, url_prefix='/conferencia/pdf')

@bp.route('/annotate/<job_id>/<filename>')
@login_required
@role_required(['admin', 'interno_unique'])
def annotate_pdf(job_id, filename):
    """
    Adiciona anotações ao PDF com os resultados da conferência
    """
    try:
        # Busca os dados do job
        job_data = supabase.table('conferencia_jobs').select('*').eq('id', job_id).execute()
        
        if not job_data.data:
            return jsonify({'status': 'error', 'message': 'Job não encontrado'}), 404
        
        job = job_data.data[0]
        
        # Encontra o arquivo no job
        file_info = None
        for arquivo in job['arquivos']:
            if arquivo['filename'] == filename:
                file_info = arquivo
                break
        
        if not file_info:
            return jsonify({'status': 'error', 'message': 'Arquivo não encontrado'}), 404
            
        if not file_info.get('result'):
            return jsonify({'status': 'error', 'message': 'Resultado não disponível para este arquivo'}), 400
            
        # Caminho do arquivo original
        pdf_path = file_info['path']
        
        # Verifica se o arquivo existe
        if not os.path.exists(pdf_path):
            return jsonify({'status': 'error', 'message': 'Arquivo não encontrado no sistema'}), 404
            
        # Cria um diretório temporário para o PDF anotado
        with tempfile.TemporaryDirectory() as temp_dir:
            # Converte as páginas do PDF para imagens
            images = convert_from_path(pdf_path)
            
            # Para cada página, adiciona anotações
            annotated_images = []
            for i, img in enumerate(images):
                # Cria uma cópia da imagem para anotação
                annotated = img.copy()
                draw = ImageDraw.Draw(annotated)
                
                # Define fonte para as anotações (você pode precisar ajustar o caminho para uma fonte disponível)
                try:
                    font = ImageFont.truetype("arial.ttf", 20)
                except IOError:
                    # Fallback para fonte padrão
                    font = ImageFont.load_default()
                
                # Adiciona cabeçalho de anotação
                draw.rectangle([(0, 0), (img.width, 60)], fill=(66, 133, 244, 128))
                draw.text((20, 20), f"Conferência Documental IA - {job['tipo_conferencia'].upper()}", fill=(255, 255, 255), font=font)
                
                # Adiciona rodapé com resumo
                y_pos = img.height - 100
                draw.rectangle([(0, y_pos), (img.width, img.height)], fill=(66, 133, 244, 128))
                
                # Adiciona informações do resultado
                result = file_info['result']
                sumario = result['sumario']
                status_text = "OK" if sumario['status'] == 'ok' else "ALERTA" if sumario['status'] == 'alerta' else "ERRO"
                
                draw.text((20, y_pos + 20), 
                    f"Status: {status_text} | Erros Críticos: {sumario['total_erros_criticos']} | " +
                    f"Alertas: {sumario['total_alertas']} | Observações: {sumario['total_observacoes']}", 
                    fill=(255, 255, 255), font=font)
                
                draw.text((20, y_pos + 60), f"Conclusão: {sumario['conclusao'][:100]}{'...' if len(sumario['conclusao']) > 100 else ''}", 
                    fill=(255, 255, 255), font=font)
                
                # Salva a imagem anotada
                annotated_path = os.path.join(temp_dir, f"page_{i}.jpg")
                annotated.save(annotated_path, "JPEG")
                annotated_images.append(annotated_path)
            
            # Cria o PDF anotado
            output_pdf_path = os.path.join(temp_dir, f"{filename}_annotated.pdf")
            annotated_pdf = PyPDF2.PdfWriter()
            
            for img_path in annotated_images:
                img = Image.open(img_path)
                pdf_bytes = io.BytesIO()
                img.save(pdf_bytes, format='PDF')
                pdf_bytes.seek(0)
                
                # Adiciona a página ao PDF final
                reader = PyPDF2.PdfReader(pdf_bytes)
                annotated_pdf.add_page(reader.pages[0])
            
            # Salva o PDF final
            with open(output_pdf_path, 'wb') as f:
                annotated_pdf.write(f)
            
            # Retorna o arquivo PDF anotado
            return send_file(output_pdf_path, 
                            mimetype='application/pdf',
                            as_attachment=True,
                            download_name=f"{filename}_anotado.pdf")
                
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erro ao anotar PDF: {str(e)}'}), 500
