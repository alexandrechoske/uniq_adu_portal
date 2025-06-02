@bp.route('/check-session', methods=['GET'])
def check_session():
    """
    Endpoint para verificar e atualizar o status da sessão
    """
    try:
        # Verificar se o usuário está logado
        if not session.get('user'):
            return jsonify({
                'status': 'error',
                'message': 'Usuário não autenticado',
                'code': 'auth_required'
            }), 401
        
        # Atualizar informações do usuário usando o novo sistema de permissões
        user_id = session['user']['id']
        user_role = session['user']['role']
        
        # Buscar permissões atualizadas
        permissions = get_user_permissions(user_id, user_role)
        session['permissions'] = permissions
        
        # Para clientes_unique, atualizar status do agente na sessão também
        if user_role == 'cliente_unique':
            session['user']['agent_status'] = {
                'is_active': permissions.get('is_active', False),
                'numero': permissions.get('agent_number'),
                'aceite_termos': permissions.get('terms_accepted', False)
            }
            session['user']['user_companies'] = permissions.get('accessible_companies', [])
        
        # Responder com sucesso e incluir as permissões
        return jsonify({
            'status': 'success',
            'message': 'Sessão válida',
            'user_role': user_role,
            'permissions': permissions
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
