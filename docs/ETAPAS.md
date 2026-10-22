# Registro da implementação por etapas

Cada etapa foi validada antes de avançar. Caminhos são relativos à raiz; comandos
usam o Python do ambiente virtual. Etapa 1 foi entregue separadamente.

| Etapa | Arquivos principais | Validação executada |
| --- | --- | --- |
| 1 — Estrutura | config.py, connection.py, pacotes, requirements, .env.example, README | 24 testes iniciais, init_db e pip check |
| 2 — Simulador | data_sources/readings.py, simulator.py | test_simulator: seed, suavidade, carga e integração kWh |
| 3 — Aquisição | base.py, factory.py, tuya.py, config.py | test_sources e test_config |
| 4 — Banco | database/models.py, repository.py | test_repository e test_database |
| 5 — Ingestão | services/ingestion.py, run_collector.py, generate_history.py | test_ingestion |
| 6 — Análises | services/analytics.py | test_analytics com dados conhecidos |
| 7 — Custos | services/energy.py | test_energy |
| 8 — Alertas | services/alerts.py, AlertRecord | test_alerts |
| 9 — Dashboard | dashboard/app.py, .streamlit/config.toml | test_dashboard: vazio, preenchido e filtros |
| 10 — Relatório | services/reports.py, generate_report.py, botão na interface | test_reports e test_dashboard |
| 11 — Features | ml/features.py | test_features: NaN, cronologia e vazamento |
| 12 — Baselines | ml/evaluate.py, evaluate_baselines.py | test_baselines; execução com 60 dias e JSON salvo |
| 13 — Modelos | ml/train.py, train_model.py | test_training; treinamento real executado |
| 14 — Previsão | ml/predict.py, scripts/predict.py | test_prediction; sete dias exportados |
| 15 — ML na interface | dashboard/forecast.py, relatório com previsão | test_dashboard_forecast e test_dashboard |
| 16 — Suíte | test_system_edges.py e anteriores | Suíte completa: 55 testes nesta etapa |
| 17 — Demonstração | services/demo.py, setup_demo.py | test_demo: fluxo do zero e backup consistente |
| 18 — Tuya | docs/TUYA.md, config.py | test_sources: sem rede e sem exposição de segredos |
| 19 — Operação | logging_config.py, maintenance.py, CLIs | test_maintenance e test_dashboard |
| 20 — Documentação | README, ETAPAS.md, requirements-lock.txt | Revisão dos comandos e preparação de cópia limpa |
| 21 — Validação final | Cópia limpa e artefatos de apresentação | Resultado registrado em VALIDACAO.md após execução |

Para reproduzir cada teste, execute `python -m pytest tests/<nome>.py -q`.
`python scripts/setup_demo.py --days 60` prepara a apresentação completa.
`python -m streamlit run app/dashboard/app.py` abre a interface.

Correções verificadas durante a execução: diretório temporário do pytest com
permissão local; recorte do gráfico após a integração para preservar deltas;
contagem de intervalos excluídos mesmo sem consumo válido; projeção mensal limitada
à semana recente. Na instalação limpa, o diretório temporário foi ajustado para
`.pytest_tmp`, diretamente na raiz, sem depender da existência prévia do cache.
A documentação explica as aproximações e limitações restantes.
