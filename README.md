# ⚡ Trabalho Prático: Apache Cassandra (NoSQL)

Projeto prático e acadêmico para o seminário de **Bancos de Dados Não Relacionais**.

* **Grupo:** Grupo 05 — Apache Cassandra
* **Data da Apresentação:** 11/11/2026 (30 minutos)
* **Objetivo:** Demonstrar conceitos teóricos e operação prática de um cluster NoSQL distribuído com tolerância a falhas e grande volume de dados.

---

## 🧠 Cérebro do Projeto (Documentação Completa)

Toda a inteligência, requisitos e roteiros do projeto estão organizados na pasta **[`cerebro/`](file:///c:/Users/jsous/Desktop/NoSql-database/cerebro/README.md)**:

1. **[Requisitos e Avaliação](file:///c:/Users/jsous/Desktop/NoSql-database/cerebro/REQUISITOS_E_AVALIACAO.md):** Matriz 1:1 com o edital do professor (5,0 pontos).
2. **[Arquitetura e Modelagem](file:///c:/Users/jsous/Desktop/NoSql-database/cerebro/ARQUITETURA_E_MODELAGEM.md):** Fundamentação teórica (Masterless, Gossip, LSM-Tree, CAP, Partições).
3. **[Como Rodar](file:///c:/Users/jsous/Desktop/NoSql-database/cerebro/COMO_RODAR.md):** Guia operacional passo a passo testado.
4. **[Status de Conclusão](file:///c:/Users/jsous/Desktop/NoSql-database/cerebro/STATUS_CONCLUSAO.md):** Checklist de tarefas e progresso.
5. **[Roteiro de Apresentação](file:///c:/Users/jsous/Desktop/NoSql-database/cerebro/ROTEIRO_APRESENTACAO.md):** Roteiro cronometrado para os 30 minutos com divisão de falas e respostas para perguntas do professor.

---

## 🚀 Como Executar o Cluster Distribuído

### 1. Subir o Cluster de 2 Nós
```bash
docker compose up -d --build
```
*O cluster sobe com 2 nós comunicando-se via Gossip e aplica automaticamente o Keyspace `telemetria` com fator de replicação 2.*

### 2. Verificar a Saúde do Cluster no Anel
```bash
docker compose exec cassandra-node1 nodetool status
```
*Ambos os nós devem aparecer com status `UN` (Up / Normal).*

### 3. Acessar o Terminal CQL Interativo
```bash
docker compose exec cassandra-node1 cqlsh -u cassandra -p cassandra
```

---

## 📊 Demonstração com Grande Volume de Dados (50.000 Registros)

1. Gere o arquivo de dados sintéticos:
   ```bash
   python scripts/gerar_dados_massa.py
   ```
2. Importe em lote com streaming nativo do Cassandra:
   ```bash
   docker compose exec -T cassandra-node1 cqlsh -u cassandra -p cassandra -e "COPY telemetria.sensores_iot (sensor_id, data_leitura, timestamp, temperatura, umidade, tensao_bateria, status) FROM '/dados/dados_sensores.csv' WITH HEADER = TRUE;"
   ```
3. Consulte com rastreamento da árvore de execução:
   ```sql
   USE telemetria;
   TRACING ON;
   SELECT * FROM sensores_iot WHERE sensor_id = 'SENSOR-SP-001' LIMIT 5;
   ```

---

## 🔌 Conexão Visual (DBeaver ou Extensão VS Code)

* **Host:** `localhost`
* **Porta:** `9042`
* **Usuário:** `cassandra` ou `root`
* **Senha:** `cassandra` ou `root`
* **Keyspaces disponíveis:** `telemetria` e `app`

![Extensão](imgs/image.png)

![Database](imgs/database.png)

---

## 🧹 Limpeza do Ambiente Docker

```bash
docker compose down -v
```