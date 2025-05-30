# Add endpoints for checking status and getting results
@bp.route('/status/<job_id>')
@login_required
@role_required(['admin', 'interno_unique'])
def check_status(job_id):
    """Endpoint para verificar o status de um job"""
    try:
        # Tenta buscar no Supabase
        job_data = supabase.table('conferencia_jobs').select('*').eq('id', job_id).execute()
        
        if job_data.data:
            job = job_data.data[0]
            
            # Calcula o progresso
            progress = 0
            if job['total_arquivos'] > 0:
                progress = int((job['arquivos_processados'] / job['total_arquivos']) * 100)
            
            return jsonify({
                'status': 'success',
                'job': {
                    'id': job['id'],
                    'status': job['status'],
                    'progress': progress,
                    'arquivos_processados': job['arquivos_processados'],
                    'total_arquivos': job['total_arquivos']
                }
            })
        
        # Fallback para armazenamento em memória
        elif job_id in jobs:
            job = jobs[job_id]
            
            # Calcula o progresso
            progress = 0
            if job['total_arquivos'] > 0:
                progress = int((job['arquivos_processados'] / job['total_arquivos']) * 100)
            
            return jsonify({
                'status': 'success',
                'job': {
                    'id': job['id'],
                    'status': job['status'],
                    'progress': progress,
                    'arquivos_processados': job['arquivos_processados'],
                    'total_arquivos': job['total_arquivos']
                }
            })
        
        else:
            return jsonify({'status': 'error', 'message': 'Job não encontrado'}), 404
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erro ao verificar status: {str(e)}'}), 500

@bp.route('/result/<job_id>')
@login_required
@role_required(['admin', 'interno_unique'])
def get_result(job_id):
    """Endpoint para obter os resultados de um job"""
    try:
        # Tenta buscar no Supabase
        job_data = supabase.table('conferencia_jobs').select('*').eq('id', job_id).execute()
        
        if job_data.data:
            job = job_data.data[0]
            return jsonify({'status': 'success', 'job': job})
        
        # Fallback para armazenamento em memória
        elif job_id in jobs:
            job = jobs[job_id]
            return jsonify({'status': 'success', 'job': job})
        
        else:
            return jsonify({'status': 'error', 'message': 'Job não encontrado'}), 404
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erro ao obter resultados: {str(e)}'}), 500
