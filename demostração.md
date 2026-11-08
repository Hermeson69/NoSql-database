# Guia Pratico de Demonstracao: Apache Cassandra

Este documento apresenta o roteiro exato, item a item, correspondente ao slide de Demonstracao da disciplina:
1. Recursos do banco (interfaces, arquitetura, etc.)
2. Esquema simples de armazenamento e consulta (com grande volume de dados)
3. Planos e arvores de execucao de consultas
4. Funcionamento de forma distribuida (mais de uma maquina)

---

## Preparacao Inicial

Execute na raiz do projeto (`/home/raildom/Downloads/NoSql-database`):

```bash
docker compose up -d
```

Aguarde cerca de 45 segundos para a inicializacao completa da JVM do Cassandra em ambos os nos.

---

## Item 1: Recursos do Banco (Interfaces e Arquitetura)

### 1.1 Arquitetura Teorica a Explicar
* **Classificacao:** NoSQL orientado a Familia de Colunas (Wide-Column Store).
* **Topologia Masterless:** Nao existe no mestre nem no escravo. Todos os nos possuem o mesmo papel no cluster e comunicam o estado do anel via protocolo Gossip (porta 7000).
* **Escalabilidade Linear:** Novos nos podem ser adicionados sem parada do servico.

### 1.2 Demonstracao das Interfaces Disponiveis
O projeto conta com tres formas de interacao que devem ser demonstradas:

1. **Interface de Administracao do Cluster (`nodetool`):**
   Utilizada para monitoramento, operacoes de anel, compactacao e reparos.
   ```bash
   docker compose exec cassandra-node1 nodetool info
   ```

2. **Interface de Linha de Comando Nativa (`cqlsh`):**
   Terminal interativo que utiliza o protocolo binario nativo (porta 9042).
   ```bash
   docker compose exec cassandra-node1 cqlsh -u cassandra -p cassandra
   ```

3. **Interface Visual (IDE / Extensao CQL do VS Code / DBeaver):**
   Conexao configurada em `localhost:9042`, permitindo inspecao de metadados, navegacao de keyspaces e execucao de scripts CQL diretamente pela IDE.

---

## Item 2: Esquema Simples de Armazenamento e Consulta

Acesse o console do CQL:

```bash
docker compose exec cassandra-node1 cqlsh -u cassandra -p cassandra
```

### 2.1 Apresentar o Esquema de Dados (Modelagem NoSQL)
Execute:

```sql
USE telemetria;
DESCRIBE TABLE sensores_iot;
```

**Explicacao tecnica do esquema:**
```sql
CREATE TABLE telemetria.sensores_iot (
    sensor_id text,
    data_leitura date,
    timestamp timestamp,
    temperatura double,
    umidade double,
    tensao_bateria double,
    status text,
    PRIMARY KEY ((sensor_id, data_leitura), timestamp)
) WITH CLUSTERING ORDER BY (timestamp DESC);
```
* **Chave de Particao Composta `(sensor_id, data_leitura)`:** Define a distribuicao dos dados no anel. Todas as medicoes de um mesmo sensor em um determinado dia residem no mesmo no fisico, otimizando gravacoes e leituras sequenciais.
* **Chave de Clusterizacao `timestamp DESC`:** Ordena as colunas internamente no disco (SSTable) em ordem cronologica decrescente.

### 2.2 Demonstracao com Grande Volume de Dados (50.000 Registros)
Verifique a contagem de registros na tabela:

```sql
SELECT COUNT(*) FROM telemetria.sensores_iot;
```
*Saida esperada: aproximadamente 50.000 registros.*

### 2.3 Executar Consulta Otimizada por Particao
Demonstre a recuperacao imediata das medicoes mais recentes de um sensor especifico:

```sql
SELECT sensor_id, data_leitura, timestamp, temperatura, umidade, status 
FROM telemetria.sensores_iot 
WHERE sensor_id = 'SENSOR-SP-001' AND data_leitura = '2026-10-24' 
LIMIT 5;
```

---

## Item 3: Planos e Arvores de Execucao (`TRACING ON`)

Como o Apache Cassandra e um banco NoSQL desnormalizado, nao ha mecanismo de `EXPLAIN` relacional com juncoes (JOINs). O plano e o fluxo de execucao sao auditados com o comando `TRACING ON`.

### 3.1 Ativar o Rastreamento
Ainda no `cqlsh`, execute:

```sql
TRACING ON;
```

### 3.2 Executar a Consulta Rastreando o Plano
```sql
SELECT * FROM telemetria.sensores_iot 
WHERE sensor_id = 'SENSOR-SP-001' AND data_leitura = '2026-10-24' 
LIMIT 3;
```

### 3.3 Explicacao dos Eventos Gerados na Arvore de Execucao
Observe e aponte para o professor as seguintes etapas que aparecem na secao `Tracing session`:
1. **Identificacao do No Coordenador:** O no que recebe a requisicao assume o papel de coordenador da transacao.
2. **Calculo do Token Murmur3:** O Cassandra calcula a funcao hash sobre `(sensor_id, data_leitura)` para identificar quais nos do anel sao responsaveis pela replica.
3. **Consulta ao Bloom Filter:** Verificacao em memoria RAM para evitar operacoes de I/O desnecessarias caso o dado nao exista na SSTable.
4. **Leitura na MemTable e SSTables:** Recuperacao do dado da memoria (MemTable) e dos arquivos imutaveis em disco (SSTables).
5. **Tempo Total de Execucao:** A consulta e resolvida na ordem de grandeza de 1 a 3 milissegundos.

Para desativar o rastreamento em seguida:
```sql
TRACING OFF;
```

---

## Item 4: Funcionamento de Forma Distribuida (Mais de uma Maquina)

Para demonstrar o funcionamento distribuido, execute no terminal:

```bash
docker compose exec cassandra-node1 nodetool status
```

### 4.1 Evidencias do Cluster Multi-No
A tabela exibida apresenta as seguintes informacoes criticas:
```text
Datacenter: dc1
===============
Status=Up/Down
|/ State=Normal/Leaving/Joining/Moving
--  Address     Load       Tokens  Owns (effective)  Host ID                               Rack
UN  172.20.0.2  150.2 KiB  16      100.0%            a1b2c3d4-e5f6-7890-1234-567890abcdef  rack1
UN  172.20.0.3  140.8 KiB  16      100.0%            f6e5d4c3-b2a1-0987-4321-fedcba098765  rack1
```
* **Status UN:** Significa `Up` e `Normal` para cada no.
* **Tokens e Owns:** Mostra a divisao uniforme da posse das faixas de tokens do anel.
* **Fator de Replicacao:** Mostre o keyspace configurado com replicação entre ambos os nos:
  ```sql
  DESCRIBE KEYSPACE telemetria;
  ```
  *(replication_factor = 2: garantia de que nenhuma maquina e ponto unico de falha).*

### 4.2 Teste Pratico de Tolerancia a Falhas (Opcional, se solicitado)
1. Desligue o segundo no:
   ```bash
   docker compose stop cassandra-node2
   ```
2. Verifique o status no terminal (o no 2 ficara `DN` - Down/Normal):
   ```bash
   docker compose exec cassandra-node1 nodetool status
   ```
3. Faca uma consulta no no 1:
   ```bash
   docker compose exec cassandra-node1 cqlsh -u cassandra -p cassandra -e "SELECT * FROM telemetria.sensores_iot LIMIT 3;"
   ```
   *A consulta responde com sucesso sem parada do servico.*
4. Religue o no secundario:
   ```bash
   docker compose start cassandra-node2
   ```

---

## Finalizacao

Para encerrar o cluster apos a apresentacao:
```bash
docker compose down
```
