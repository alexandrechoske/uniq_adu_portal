# Configuração do Storage Supabase - Sistema de Documentos
# UniSystem Portal - Document Management Setup

## 1. CRIAÇÃO DO BUCKET

### 1.1 Criar Bucket via Dashboard Supabase:
```
Nome do Bucket: processos-documentos
Público: false (privado para segurança)
File size limit: 50MB por arquivo
Allowed MIME types: 
- application/pdf
- image/jpeg, image/png, image/gif, image/webp
- application/vnd.ms-excel
- application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
- application/msword
- application/vnd.openxmlformats-officedocument.wordprocessingml.document
- text/plain, text/csv
- application/zip
```

### 1.2 Estrutura de Pastas:
```
processos-documentos/
├── 2025/
│   ├── 01/
│   │   ├── UN25-0001/
│   │   │   ├── fatura-comercial-{timestamp}.pdf
│   │   │   ├── conhecimento-embarque-{timestamp}.pdf
│   │   │   └── packing-list-{timestamp}.xlsx
│   │   └── UN25-0002/
│   └── 02/
└── 2024/
    └── 12/
```

## 2. POLÍTICAS RLS DO STORAGE

### 2.1 Política de Upload (INSERT)
```sql
-- Apenas usuários admin/interno podem fazer upload
CREATE POLICY "Upload documentos admin/interno" ON storage.objects
FOR INSERT WITH CHECK (
    bucket_id = 'processos-documentos' AND
    EXISTS (
        SELECT 1 FROM auth.users
        WHERE auth.users.id = auth.uid()
        AND (
            auth.users.raw_user_meta_data->>'role' = 'admin' OR
            auth.users.raw_user_meta_data->>'role' = 'interno_unique'
        )
    )
);
```

### 2.2 Política de Visualização (SELECT)
```sql
-- Admin/interno veem tudo, clientes só o que é permitido
CREATE POLICY "Download documentos controle acesso" ON storage.objects
FOR SELECT USING (
    bucket_id = 'processos-documentos' AND
    (
        -- Admin/interno: acesso total
        EXISTS (
            SELECT 1 FROM auth.users
            WHERE auth.users.id = auth.uid()
            AND (
                auth.users.raw_user_meta_data->>'role' = 'admin' OR
                auth.users.raw_user_meta_data->>'role' = 'interno_unique'
            )
        )
        OR
        -- Cliente: apenas documentos visíveis e da própria empresa
        EXISTS (
            SELECT 1 FROM documentos_processos dp
            JOIN importacoes_processos ip ON dp.ref_unique = ip.ref_unique
            JOIN auth.users au ON (
                au.id = auth.uid() AND
                au.raw_user_meta_data->>'role' = 'cliente_unique' AND
                ip.cnpj_importador = ANY(
                    string_to_array(au.raw_user_meta_data->>'companies', ',')
                )
            )
            WHERE dp.storage_path = storage.objects.name
            AND dp.visivel_cliente = true
            AND dp.ativo = true
        )
    )
);
```

### 2.3 Política de Exclusão (DELETE)
```sql
-- Apenas admin pode excluir fisicamente
CREATE POLICY "Delete documentos admin" ON storage.objects
FOR DELETE USING (
    bucket_id = 'processos-documentos' AND
    EXISTS (
        SELECT 1 FROM auth.users
        WHERE auth.users.id = auth.uid()
        AND auth.users.raw_user_meta_data->>'role' = 'admin'
    )
);
```

## 3. CONFIGURAÇÕES DE SEGURANÇA

### 3.1 Validações de Arquivo:
- Tamanho máximo: 50MB
- Tipos MIME permitidos (whitelist)
- Scan de vírus (se disponível)
- Validação de extensão vs MIME type

### 3.2 Nomenclatura de Arquivos:
```
Padrão: {ano}/{mes}/{ref_unique}/{nome-sanitizado}-{timestamp}.{ext}
Exemplo: 2025/01/UN25-0001/fatura-comercial-20250122144530.pdf
```

### 3.3 Metadados:
- `ref_unique`: Referência do processo
- `uploaded_by`: ID do usuário que fez upload
- `original_name`: Nome original do arquivo
- `content_type`: MIME type verificado

## 4. COMANDOS SUPABASE CLI (Opcional)

### 4.1 Criar bucket via CLI:
```bash
supabase storage create-bucket processos-documentos --public=false
```

### 4.2 Aplicar políticas via CLI:
```bash
supabase db reset
# Ou aplicar individualmente cada política
```

## 5. VARIÁVEIS DE AMBIENTE

### 5.1 Adicionar ao .env:
```env
# Storage Configuration
SUPABASE_STORAGE_BUCKET=processos-documentos
MAX_FILE_SIZE_MB=50
ALLOWED_EXTENSIONS=pdf,jpg,jpeg,png,gif,webp,xlsx,xls,docx,doc,txt,csv,zip
VIRUS_SCAN_ENABLED=false
```

## 6. MONITORAMENTO E LOGS

### 6.1 Métricas para acompanhar:
- Número de uploads por dia
- Tamanho total de storage usado
- Tipos de arquivo mais enviados
- Erros de upload

### 6.2 Logs importantes:
- Tentativas de upload não autorizadas
- Downloads de documentos
- Modificações de visibilidade
- Exclusões de arquivos

## 7. BACKUP E RECUPERAÇÃO

### 7.1 Estratégia de backup:
- Backup automático do Supabase inclui storage
- Considerar backup adicional para documentos críticos
- Retenção: 30 dias para backups automáticos

### 7.2 Plano de recuperação:
- Documentação do processo de restore
- Testes regulares de recuperação
- Contacts de suporte Supabase
