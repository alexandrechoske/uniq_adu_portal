-- Script para verificar e configurar RLS na tabela users
-- Execute este script no SQL Editor do Supabase se necessário

-- Verificar se RLS está habilitado
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE tablename = 'users';

-- Se RLS estiver habilitado, verificar as políticas
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies 
WHERE tablename = 'users';

-- Se necessário, criar política para permitir que admins excluam usuários
-- (Execute apenas se não existir uma política adequada)
/*
CREATE POLICY "Admins can delete users" ON users
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM users u 
            WHERE u.id = auth.uid() 
            AND u.role = 'admin'
        )
    );
*/

-- Alternativamente, se necessário, desabilitar RLS temporariamente para debug
-- (CUIDADO: Isso remove todas as proteções de segurança)
-- ALTER TABLE users DISABLE ROW LEVEL SECURITY;
