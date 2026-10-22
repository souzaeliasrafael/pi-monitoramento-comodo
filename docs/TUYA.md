# Integração futura com Tuya

Esta versão não usa rede, credenciais, SDK ou dispositivos reais. Selecionar
`DATA_SOURCE=tuya` retorna uma mensagem explícita de funcionalidade indisponível.
Não existe fallback silencioso que apresente simulação como leitura real.

O contrato está em `app/data_sources/base.py`; cada adaptador entrega `Reading`
de `app/data_sources/readings.py`. O único ponto de seleção é
`app/data_sources/factory.py`. Implemente a aquisição em `app/data_sources/tuya.py`
quando houver dispositivos e autorização para acesso à API.

## Passos futuros

1. Configurar `TUYA_ACCESS_ID`, `TUYA_ACCESS_SECRET`, `TUYA_ENDPOINT` e
   `TUYA_DEVICE_IDS` exclusivamente no ambiente ou `.env`, sem versionar segredos.
2. Consultar a documentação oficial vigente para região, autenticação, assinatura,
   renovação de tokens, limites de requisições e códigos de status de cada produto.
3. Criar um mapeamento explícito dos IDs físicos para IDs estáveis do sistema.
   Não presumir nomes nem escalas de datapoints iguais entre modelos.
4. Converter temperatura para °C, umidade para %, tensão para V, corrente para A,
   potência para W e contador acumulado para kWh, de acordo com a escala declarada
   por cada dispositivo. Não confundir consumo de um período com contador acumulado.
5. Converter horários recebidos para America/Sao_Paulo e remover o offset apenas
   na fronteira do contrato atual. Descartar leituras sem timestamp confiável.
6. Tratar timeout, indisponibilidade, token expirado e limite de requisições. Não
   imprimir respostas brutas, headers de autorização nem credenciais em logs.
7. Testar o adaptador com respostas gravadas sem segredos, sem rede na suíte.
8. Validar consistência de potência, contador e períodos antes de usar dados reais.

O contador precisa manter continuidade. A análise atual exclui deltas negativos e
intervalos maiores que uma hora e mostra cobertura incompleta. Para medidores que
reiniciam o contador, definir uma política explícita de normalização no adaptador;
não inventar o consumo perdido.

Os serviços, SQLite, relatórios e ML dependem do contrato normalizado, não de um SDK
Tuya. `resume_simulator` restaura exclusivamente o estado sintético; um adaptador
real recebe o contador do próprio medidor.

Ao migrar, usar uma base separada, atualizar a identificação da origem no dashboard
e nos relatórios e realizar validação com medições reais. O texto de simulação da
interface é proposital e não deve ser removido enquanto a origem continuar sintética.
O modelo sintético não deve ser reaproveitado como modelo validado para o local real.
