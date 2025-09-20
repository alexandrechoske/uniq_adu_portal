#!/bin/bash

# Script para parar UniSystem Portal
echo "🛑 Parando UniSystem Portal..."

# Verifica se existe arquivo PID
if [ -f app.pid ]; then
    APP_PID=$(cat app.pid)
    
    if kill -0 $APP_PID 2>/dev/null; then
        echo "📝 Parando processo PID: $APP_PID"
        kill $APP_PID
        rm app.pid
        echo "✅ Aplicação parada com sucesso!"
    else
        echo "⚠️ Processo não estava rodando"
        rm app.pid
    fi
else
    echo "⚠️ Arquivo PID não encontrado, tentando parar por nome do processo..."
    pkill -f "python app.py" && echo "✅ Processo parado!" || echo "❌ Nenhum processo encontrado"
fi
