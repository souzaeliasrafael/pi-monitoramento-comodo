#!/bin/sh
# Inicialização no Railway: banco, modelos, relatórios e logs ficam no volume,
# o coletor roda em segundo plano e o Streamlit atende na porta do Railway.
set -e

DATA_DIR="${RAILWAY_VOLUME_MOUNT_PATH:-/data}"
mkdir -p "$DATA_DIR/models" "$DATA_DIR/reports" "$DATA_DIR/logs"
for dir in models reports logs; do
    rm -rf "$dir"
    ln -s "$DATA_DIR/$dir" "$dir"
done

export DATABASE_URL="${DATABASE_URL:-sqlite:///$DATA_DIR/monitoramento.db}"

# Primeiro deploy: cria o histórico inicial, treina o modelo e gera a previsão.
if [ ! -f "$DATA_DIR/monitoramento.db" ]; then
    python scripts/setup_demo.py --days "${INITIAL_DAYS:-60}"
fi

# Reinicia o coletor automaticamente se ele encerrar com erro.
(while true; do python scripts/run_collector.py; sleep 30; done) &

exec python -m streamlit run app/dashboard/app.py \
    --server.address 0.0.0.0 --server.port "${PORT:-8501}" --server.headless true
