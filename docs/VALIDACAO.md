# Validação final — 04/10/2026

## Cenário residencial atualizado

Em atualização posterior, os 5.000 registros foram regenerados para duas lâmpadas
LED de 9 W, cinco horas/dia (18h–23h), sem outras cargas. Tarifa Enel SP residencial:
R$ 0,78938/kWh. Projeção de outubro: 2,79 kWh e R$ 2,20, sem tributos e adicionais.
Modelo, previsão e relatório atualizados. Os resultados abaixo são históricos de
validações anteriores; não representam a carga residencial atual.

## Atualização posterior: Mauá e base compacta

A base de apresentação foi regenerada com `setup_demo.py --days 33 --records 5000`:
**5.000 leituras**, 1.250 por dispositivo, de 01/09/2026 até 04/10/2026 às 11:10.
O banco anterior foi preservado em backup. Modelo, métricas de baseline, previsão
e relatório foram recalculados. Não houve intervalos excluídos no cálculo energético.
O perfil térmico passou a usar médias climatológicas mensais de Mauá/SP conforme
a referência e as hipóteses descritas no README. Média das temperaturas geradas:
20,20 °C; extremos de 13,63 a 30,56 °C incluindo diferenças de posição e eventos.
Esses extremos são sintéticos e não representam registros meteorológicos observados.

O banner inicial foi removido e o navegador confirmou a indicação `5.000 registros`.
Os resultados de 60 dias abaixo registram a validação anterior e não descrevem
os artefatos atuais da demonstração compacta.

Validação em Windows, Python 3.14.7, com dependências registradas em
requirements-lock.txt. Todos os dados usados foram simulados.

## Instalação limpa

Foi criada uma cópia contendo apenas código, configuração de exemplo, testes e
documentação em `.validation/fresh-t4wr0xge`, sem banco, modelo ou ambiente virtual.
Nela foram executados:

1. `python -m venv .venv`.
2. Instalação de `requirements.txt` no ambiente novo.
3. Cópia de `.env.example` para `.env`.
4. `python -m pip check`: sem dependências quebradas.
5. `python -m scripts.init_db`: tabelas criadas.
6. `python scripts/generate_history.py --days 60`: 23.044 leituras históricas.
7. `python scripts/evaluate_baselines.py`: métricas JSON salvas.
8. `python scripts/train_model.py`: cinco candidatos comparados e modelo salvo.
9. `python scripts/predict.py`: sete dias previstos e CSV exportado.
10. `python scripts/generate_report.py`: HTML com análise e previsão gerado.
11. `python scripts/run_collector.py --once`: quatro novas leituras e relatório
    semanal automático, sem traceback.
12. `python -m pytest -q`: **59 testes passaram em 13,44 s**.
13. `python scripts/setup_demo.py --days 60`: fluxo completo com backup, 23.224
    leituras incluindo o dia parcial e 47 alertas agrupados.

O teste inicial da cópia limpa revelou que o diretório temporário do pytest
dependia de um cache pré-existente. A configuração foi corrigida para `.pytest_tmp`
diretamente na raiz e toda a suíte foi executada novamente com sucesso.

## Interface

O dashboard principal foi iniciado em `127.0.0.1:8501` e inspecionado no navegador.
Foram confirmados os seis indicadores, histórico, aviso de simulação, previsão,
comparação de modelos e controle de relatório. Os indicadores foram organizados
em duas linhas para evitar truncamento no painel estreito do Codex.
AppTest cobre banco vazio, preenchido, filtro de sensor e painel de previsão com modelo.

## Resultado demonstrativo

Seed 42, histórico completo de 05/08/2026 a 03/10/2026, mais dia atual parcial:

| Medida | Resultado |
| --- | --- |
| Modelo selecionado | RandomForestRegressor |
| MAE de validação | 2,4122 kWh/dia |
| MAE de teste | 1,8566 kWh/dia |
| RMSE de teste | 3,1313 kWh/dia |
| Amostras de teste | 11 dias |
| Previsão de 04/10 a 10/10/2026 | 106,09 kWh |
| Custo previsto, tarifa 0,95 | R$ 100,78 |

O teste reservado não foi usado na seleção. O modelo salvo foi reajustado em
todos os dados depois da avaliação. Esses resultados demonstram o funcionamento
do pipeline, **não validam previsão para o estabelecimento real**.

## Limites da validação

Sem conexão Tuya, sem implantação em nuvem, sem dispositivos físicos, sem PDF
automático e sem teste em outro sistema operacional. O relatório HTML é o formato
entregue. Operação simulada e testes não exigem internet após instalar os pacotes.


## Atualização: quatro lâmpadas e aprendizado progressivo — 04/10/2026

- 5.000 leituras preservadas, geradas novamente após cópia de segurança do banco.
- Quatro lâmpadas de 15 W; referência de 5 horas/dia com variação de ocupação.
- 13 ciclos cronológicos de Random Forest e 11 dias avaliados; MAE 0,05 kWh/dia.
- Emissão anterior ao dia previsto; valores observados só registrados após o dia
  completo. Previsões antigas são imutáveis. Origem histórica identificada no banco.
- Calendários verificados no navegador: mudar início de 28/09 para 01/09 alterou
  consumo de 2,07 para 9,81 kWh e custo de R$ 1,63 para R$ 7,74. Filtro restaurado.
- Duas casas decimais nos indicadores, gráficos, tabelas e relatório.
- Limite de umidade de 70% explicado como configuração do pedido inicial.
- Suíte: 70 testes aprovados; após ajustes de apresentação, três testes específicos
  de painel, previsão e relatório também aprovados.

A comparação inicial por divisão temporal permanece separada do ciclo progressivo:
na execução atual, Linear Regression venceu a validação inicial; Random Forest é
usado no ciclo de atualização diária, com uma janela recente de treinamento.
Os resultados anteriores neste documento são históricos e não descrevem a carga atual.


## Disjuntor inteligente e uso dinâmico — 04/10/2026

Histórico recriado com backup: 5.000 leituras, 33 dias completos. Cadastro de
cargas reduzido a nome, quantidade e potência; antigas programações são ignoradas.

- Atividade gerada: média 9,02 h/dia, sempre entre 8 e 10 h/dia.
- Atividade estimada pelas leituras: média 8,96 h/dia em todo o histórico.
- Potência amostrada: zero a 59,99 W, com níveis próximos de 15/30/45/60 W.
- Tensão: aproximadamente 215,00 a 224,94 V; corrente zero a 0,28 A.
- Consumo médio dos dias completos: 0,41 kWh/dia. Integração exata dos segmentos,
  independente da frequência de coleta. A corrente usa a simplificação P/V.
- 72 testes aprovados, incluindo reprodução determinística, energia aditiva,
  independência da frequência de amostragem, persistência e entrada de novas cargas.
- Painel verificado no navegador: disjuntor, potência em degraus, tensão, corrente,
  atividade estimada, custos por filtro e novas previsões.

A ocupação é um cenário sintético residencial; não são especificações ou medições
validadas de um fabricante. A faixa 8–10 h representa atividade do circuito, não
o funcionamento simultâneo das quatro lâmpadas durante todo esse tempo.


## Perfil de fim de semana — 04/10/2026

Os gráficos de tensão e corrente foram removidos do painel. A fonte agora encerra
toda atividade aos sábados às 12h e não gera consumo aos domingos, incluindo
cargas adicionais. A faixa de atividade de 8–10 horas é restrita aos dias úteis.
Após backup, foram recriadas 5.000 leituras e recalculados custos e previsões.

Médias verificadas no banco: 0,40 kWh/dia útil, 0,13 kWh/sábado e 0,00 kWh/domingo.
Todas as potências amostradas após as 12h dos sábados são zero; todos os totais
diários de domingo também são zero. Testes de integração garantem energia zero
entre sábado ao meio-dia e segunda-feira à meia-noite. Suíte: 73 testes aprovados.

### Filtro único entre telas — 04/10/2026
- Datas e dispositivo persistem entre Ambiente, Energia, Alertas, Previsão e Equipamentos.
- Teste integrado confirma alterações nos totais, previsões, erros e equipamentos disponíveis até a data final.
- Relatório respeita o intervalo e dispositivo selecionados; download anterior deixa de aparecer se a seleção mudar.
- Suíte completa: 73 testes aprovados.
