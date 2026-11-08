# Demonstração Prática — Apache Cassandra (NoSQL)

Roteiro completo de demonstração estruturado diretamente a partir dos requisitos do slide da apresentação:

* **Recursos do banco (interfaces, arquitetura, etc.)**
* **Mostrar um esquema simples de armazenamento e consulta de dados utilizando o banco de dados escolhido**
  * **Tentem demonstrar o uso com um grande volume de dados**
* **Planos e árvores de execução de consultas (se aplicável)**
* **Funcionamento de forma distribuída (mais de uma máquina)**

---

## 1. Recursos do Banco (Interfaces, Arquitetura, etc.)

### 1.1 Arquitetura Interna
* **Tipo do Banco:** NoSQL orientado a Família de Colunas (Wide-Column Store), baseado nos modelos do Google Bigtable e Amazon Dynamo.
* **Topologia Masterless (P2P):** Não existe nó primário nem secundário fixo. Qualquer nó pode atuar como Nó Coordenador de uma consulta.
* **Comunicação do Anel:** Os nós sincronizam metadados e estado do cluster via protocolo Gossip na porta TCP `7000`.
* **Mecanismo de Escrita e Leitura:** Estrutura baseada em LSM-Tree (Log-Structured Merge-tree) com MemTable em memória RAM, CommitLog sequencial e SSTables imutáveis gravadas em disco.

### 1.2 Interfaces Demonstradas na Prática
O ecossistema do Cassandra oferece três interfaces de acesso:

1. **Interface de Linha de Comando Nativa (`cqlsh`):**
   Acesso direto via protocolo binário nativo (porta `9042`):
   ```bash
   docker exec -it cassandra-node1 cqlsh localhost 9042
   ```
   *(No Modo B, executado no Computador 2 apontando para `cassandra-node2`).*

2. **Interface Administrativa do Nó (`nodetool`):**
   Utilitário administrativo oficial para monitorar o anel de tokens, taxas de compressão e uso de memória:
   ```bash
   docker exec -it cassandra-node1 nodetool info
   ```

3. **Interface Gráfica Visual (Extensão CQL no VS Code / DBeaver):**
   Conexão JDBC/CQL configurada em `localhost:9042` com os Keyspaces `telemetria` e `app`, permitindo navegação estrutural das tabelas e execução visual de scripts.

---

## 2. Esquema Simples de Armazenamento e Consulta de Dados

Acesse o terminal do Cassandra:
```bash
docker exec -it cassandra-node1 cqlsh localhost 9042
```
*(Ou no nó 2: `docker exec -it cassandra-node2 cqlsh localhost 9042`).*

### 2.1 Apresentação do Esquema de Dados (Modelagem NoSQL de Telemetria)
Dentro do `cqlsh`, selecione o keyspace e exiba o DDL da tabela:

```sql
USE telemetria;
DESCRIBE TABLE sensores_iot;
```

**Estrutura da Tabela:**
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

**Conceitos Fundamentais da Modelagem a Explicar:**
* **Chave de Partição Composta `(sensor_id, data_leitura)`:** Define a distribuição física dos dados no anel. O hash Murmur3 é calculado sobre essas duas colunas, garantindo que todas as leituras de um mesmo sensor em determinado dia fiquem alocadas no mesmo nó sem espalhar I/O.
* **Chave de Clusterização `timestamp DESC`:** Ordena as linhas dentro da partição fisicamente no disco em ordem cronológica decrescente.

### 2.2 Consulta Simples de Amostra
Recuperação das leituras mais recentes registradas:
```sql
SELECT * FROM telemetria.sensores_iot LIMIT 5;
```

---

## 2.1 Demonstração com Grande Volume de Dados (50.000 Registros)

### Passo 1: Geração Sintética do Volume de Dados
Caso o arquivo de dados precise ser regerado, execute no terminal do host:
```bash
python scripts/gerar_dados_massa.py
```
*O script produz 50.000 medições realistas de IoT distribuídas em 35 sensores no arquivo `dados/dados_sensores.csv` em cerca de 2 segundos.*

### Passo 2: Ingestão de Alta Performance com Comando Nativo `COPY`
Importe os 50.000 registros com streaming em lote:
```bash
docker exec -i cassandra-node1 cqlsh localhost 9042 -e "COPY telemetria.sensores_iot (sensor_id, data_leitura, timestamp, temperatura, umidade, tensao_bateria, status) FROM '/dados/dados_sensores.csv' WITH HEADER = TRUE;"
```
*Tempo de ingestão: 50.000 registros importados em aproximadamente 10 segundos.*

### Passo 3: Comprovação do Volume na Tabela
No terminal `cqlsh`:
```sql
SELECT COUNT(*) FROM telemetria.sensores_iot;
```
*Resultado comprovado: ~50.000 registros.*

### Passo 4: Consulta Otimizada por Partição com Alto Volume
Demonstração de busca pontual de alta performance mesmo com 50.000 registros:
```sql
SELECT sensor_id, data_leitura, timestamp, temperatura, umidade, status 
FROM telemetria.sensores_iot 
WHERE sensor_id = 'SENSOR-SP-001' AND data_leitura = '2026-10-24' 
LIMIT 5;
```

---

## 3. Planos e Árvores de Execução de Consultas (`TRACING ON`)

Diferente de bancos relacionais que utilizam comandos de estimativa baseados em custo como `EXPLAIN`, o Cassandra audita o plano e o caminho real da consulta no motor de armazenamento com o utilitário nativo **`TRACING`**.

### 3.1 Ativação do Rastreamento
No prompt do `cqlsh`:
```sql
USE telemetria;
TRACING ON;
```

### 3.2 Execução da Consulta com Análise de Rastreamento
```sql
SELECT * FROM telemetria.sensores_iot 
WHERE sensor_id = 'SENSOR-SP-001' AND data_leitura = '2026-10-24' 
LIMIT 5;
```

### 3.3 Eventos da Árvore de Execução a Explicar na Tela:
A saída exibirá o bloco `Tracing session` com as etapas internas em microssegundos:
1. **Identificação do Nó Coordenador:** Nó que recebe a query e gerencia o ciclo de vida da requisição.
2. **Cálculo do Token Murmur3:** O Cassandra calcula o hash da partição `(SENSOR-SP-001, 2026-10-24)` para determinar em qual réplica do cluster o dado reside.
3. **Consulta ao Bloom Filter:** Verificação em memória RAM para confirmar se a partição existe no arquivo em disco, eliminando acessos de I/O desnecessários.
4. **Fusão de MemTable com SSTables:** Recuperação e merge dos dados presentes na memória (MemTable) com os dados consolidados no disco (SSTables).
5. **Latência de Execução:** Resolução completa da consulta na ordem de grandeza de 1 a 3 milissegundos.

Para desligar o rastreamento após a demonstração:
```sql
TRACING OFF;
```

---

## 4. Funcionamento de Forma Distribuída (Mais de uma Máquina)

### 4.1 Modos Suportados de Execução Distribuída

#### Modo A: Dois Nós em Containers Isolados (Recomendado para Apresentação - Zero Risco)
Executado na raiz do projeto com portas dedicadas e comunicação real via Gossip:
```bash
docker compose up -d --build
```
* O `cassandra-node1` sobe na porta `9042` (IP virtual `172.20.0.2`).
* O `cassandra-node2` sobe na porta `9043` (IP virtual `172.20.0.3`).
* O `cassandra-init` aplica o schema e o seed com fator de replicação 2.

#### Modo B: Dois Computadores Físicos Reais (Laboratório / Wi-Fi / Radmin VPN)
* **Computador 1 (Máquina Seed - Nó 1):**
  ```powershell
  docker run -d --name cassandra-node1 -p 7000:7000 -p 9042:9042 -e CASSANDRA_CLUSTER_NAME="NoSQLCluster" -e CASSANDRA_DC="dc1" -e CASSANDRA_RACK="rack1" -e CASSANDRA_ENDPOINT_SNITCH="GossipingPropertyFileSnitch" -e CASSANDRA_BROADCAST_ADDRESS=IP_PC1 -e CASSANDRA_BROADCAST_RPC_ADDRESS=IP_PC1 -e CASSANDRA_SEEDS=IP_PC1 -e MAX_HEAP_SIZE="768M" -e HEAP_NEWSIZE="192M" -v ${PWD}/dados:/dados cassandra:5.0
  ```
* **Computador 2 (Máquina Secundária - Nó 2):**
  Executado pelo script com substituição de sessão automática:
  ```bash
  python3 scripts/cluster.py
  ```
  *(Opção 2 - Máquina 2).*

---

### 4.2 Verificação do Anel Distribuído (`nodetool status`)
Em qualquer uma das máquinas, execute no terminal:
```bash
docker exec -it cassandra-node1 nodetool status
```
*(ou `docker exec -it cassandra-node2 nodetool status` no Computador 2)*.

**Saída Esperada no Terminal:**
```text
Datacenter: dc1
===============
Status=Up/Down
|/ State=Normal/Leaving/Joining/Moving
--  Address         Load        Tokens  Owns (effective)  Host ID                               Rack
UN  10.215.120.135  119.67 KiB  16      100.0%            c3b7cae4-215a-47ca-9b09-0b44b74ff7d2  rack1
UN  10.215.120.142  119.85 KiB  16      100.0%            e0811b3b-ba9c-42b6-ad70-9a900d8e8e35  rack1
```
* **Status UN:** Comprova que ambos os nós estão Up e Normal.
* **Tokens e Owns (100.0%):** O anel compartilha a carga igualmente com fator de replicação integral.

### 4.3 Comprovação de Replicação de Dados entre Nós
1. Insira ou consulte os dados a partir do Computador 1.
2. No terminal do Computador 2, verifique a presença imediata dos mesmos dados:
   ```bash
   docker exec -it cassandra-node2 cqlsh localhost 9042 -e "SELECT count(*) FROM telemetria.sensores_iot;"
   ```
   *Comprova a sincronização e replicação em tempo real entre máquinas distintas.*

### 4.4 Teste de Tolerância a Falhas (Alta Disponibilidade ao Vivo)
1. Com o cluster em operação, derrube propositalmente o segundo nó:
   ```bash
   docker stop cassandra-node2
   ```
2. No Computador 1, consulte o status com `nodetool status`:
   * `cassandra-node1` permanece `UN` (Up / Normal).
   * `cassandra-node2` passa para `DN` (Down / Normal).
3. Execute consultas no Nó 1 sobrevivente:
   ```bash
   docker exec -it cassandra-node1 cqlsh localhost 9042 -e "SELECT * FROM telemetria.sensores_iot LIMIT 5;"
   ```
   *A consulta responde perfeitamente, comprovando a ausência de ponto único de falha (Single Point of Failure).*
4. Religue o nó secundário:
   ```bash
   docker start cassandra-node2
   ```
   *Em segundos, o nó reconecta ao anel e sincroniza novamente sem intervenção manual.*

---

## 5. Limpeza do Ambiente após a Apresentação

Para desligar os containers e liberar as portas:
```bash
docker rm -f cassandra-node1 cassandra-node2
```
*(Ou se executou via Docker Compose: `docker compose down -v`).*
