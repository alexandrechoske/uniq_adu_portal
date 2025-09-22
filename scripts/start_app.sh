#!/bin/bash

# Script para iniciar UniSystem Portal de forma persistente
echo "🚀 Iniciando UniSystem Portal..."

# Mata processos anteriores se existirem
pkill -f "python app.py" 2>/dev/null || true

# Aguarda um pouco para garantir que os processos foram terminados
sleep 1

# Inicia a aplicação em background com nohup para manter rodando
cd /workspaces/uniq_adu_portal

nohup python app.py > app.log 2>&1 &

# Guarda o PID
APP_PID=$!
echo $APP_PID > app.pid

echo "✅ Aplicação iniciada com PID: $APP_PID"
echo "📝 Logs em: app.log"
echo "🌐 Acessível em: http://localhost:5000"

# Aguarda a aplicação inicializar
echo "⏳ Aguardando inicialização..."
sleep 5

# Testa se a aplicação está respondendo
if curl -s http://localhost:5000/paginas/health > /dev/null 2>&1; then
    echo "✅ Aplicação rodando e respondendo!"
else
    echo "❌ Aplicação pode não estar respondendo ainda. Verifique os logs."
fi

echo ""
echo "Para parar a aplicação, execute: ./scripts/stop_app.sh"
echo "Para ver logs em tempo real: tail -f app.log"
