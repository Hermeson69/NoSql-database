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
   ```bash
   docker exec -it cassandra-node1 cqlsh localhost 9042
   ```
   *O que este comando faz: Abre o terminal interativo do Cassandra via protocolo binário nativo (porta 9042) para executar consultas CQL diretamente. No Modo B, use `cassandra-node2`.*

2. **Interface Administrativa do Nó (`nodetool`):**
   ```bash
   docker exec -it cassandra-node1 nodetool info
   ```
   *O que este comando faz: Exibe métricas de infraestrutura do nó, como tempo em atividade (uptime), uso de memória heap da JVM, ID do host e taxas de carga.*

3. **Interface Gráfica Visual (Extensão CQL no VS Code / DBeaver):**
   Conexão JDBC/CQL configurada em `localhost:9042` com os Keyspaces `telemetria` e `app`, permitindo navegação estrutural das tabelas e execução visual de scripts.

---

## 2. Esquema Simples de Armazenamento e Consulta de Dados

Acesse o terminal do Cassandra:
```bash
docker exec -it cassandra-node1 cqlsh localhost 9042
```
*O que este comando faz: Conecta no console interativo CQL do container para permitir a digitação de queries.*

### 2.1 Apresentação do Esquema de Dados (Modelagem NoSQL de Telemetria)
Dentro do `cqlsh`, execute o comando abaixo para visualizar a estrutura completa da tabela:

```sql
USE telemetria;
DESCRIBE TABLE sensores_iot;
```
*O que este comando faz: O `USE telemetria;` seleciona o banco/keyspace do projeto. O `DESCRIBE TABLE sensores_iot;` pede para o Cassandra imprimir na tela o código DDL completo com todas as colunas, chaves primárias e propriedades da tabela.*

> **Atenção:** O único comando que você digita no terminal é `DESCRIBE TABLE sensores_iot;`. O bloco abaixo é o que o próprio Cassandra vai imprimir na tela como resultado. Não tente digitar "PRIMARY KEY" solto no terminal.

**Saída exibida na tela pelo Cassandra:**
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
*Descrição técnica do código DDL: Define o esquema da tabela no keyspace telemetria. Contém colunas de texto (identificador do sensor e status operacional), data e horário exato (data_leitura e timestamp) e valores numéricos em ponto flutuante (temperatura em graus, umidade relativa e tensão da bateria em volts). A cláusula WITH CLUSTERING ORDER BY instrui o motor de gravação das SSTables a manter as linhas de cada partição já ordenadas fisicamente por horário decrescente direto no arquivo de dados.*

**O que você deve apontar e explicar na tela para o professor:**
* **Chave de Partição `(sensor_id, data_leitura)`:** Aponte para essa parte e explique que ela define a distribuição física dos dados no anel. O hash Murmur3 é calculado sobre essas duas colunas para alocar o dado no nó certo.
* **Chave de Clusterização `timestamp DESC`:** Aponte para o timestamp e explique que ele ordena as linhas dentro da partição fisicamente no disco em ordem cronológica decrescente.

### 2.2 Consulta Simples de Amostra
Recuperação das leituras mais recentes registradas:
```sql
SELECT * FROM telemetria.sensores_iot LIMIT 5;
```
*O que este comando faz: Busca e retorna as 5 primeiras linhas gravadas na tabela com todas as suas colunas (temperatura, umidade, status, etc.).*

---

## 2.1 Demonstração com Grande Volume de Dados (50.000 Registros)

### Passo 1: Geração Sintética do Volume de Dados
Caso o arquivo de dados precise ser regerado, execute no terminal do host:
```bash
python scripts/gerar_dados_massa.py
```
*O que este comando faz: Roda o gerador em Python para criar o arquivo CSV estruturado com 50.000 medições realistas de IoT distribuídas em 35 sensores.*

### Passo 2: Ingestão de Alta Performance com Comando Nativo `COPY`
Importe os 50.000 registros com streaming em lote:
```bash
docker exec -i cassandra-node1 cqlsh localhost 9042 -e "COPY telemetria.sensores_iot (sensor_id, data_leitura, timestamp, temperatura, umidade, tensao_bateria, status) FROM '/dados/dados_sensores.csv' WITH HEADER = TRUE;"
```
*O que este comando faz: Aciona o mecanismo nativo de streaming de alta velocidade do Cassandra para ler o CSV e gravar as 50.000 linhas no cluster em cerca de 10 segundos.*

### Passo 3: Comprovação do Volume na Tabela
No terminal `cqlsh`:
```sql
SELECT COUNT(*) FROM telemetria.sensores_iot;
```
*O que este comando faz: Realiza a contagem agregada de registros no cluster para comprovar que os 50.000 dados estão armazenados.*

### Passo 4: Consulta Otimizada por Partição com Alto Volume
Demonstração de busca pontual de alta performance mesmo com 50.000 registros:
```sql
SELECT sensor_id, data_leitura, timestamp, temperatura, umidade, status 
FROM telemetria.sensores_iot 
WHERE sensor_id = 'SENSOR-SP-001' AND data_leitura = '2026-10-24' 
LIMIT 5;
```
*O que este comando faz: Busca registros filtrando diretamente pela Chave de Partição exata. O Cassandra calcula o token hash e vai direto no local físico correto sem fazer varredura desnecessária.*

---

## 3. Planos e Árvores de Execução de Consultas (`TRACING ON`)

Diferente de bancos relacionais que utilizam comandos de estimativa baseados em custo como `EXPLAIN`, o Cassandra audita o plano e o caminho real da consulta no motor de armazenamento com o utilitário nativo **`TRACING`**.

### 3.1 Ativação do Rastreamento
No prompt do `cqlsh`:
```sql
USE telemetria;
TRACING ON;
```
*O que este comando faz: Liga o rastreador de performance da sessão, fazendo com que qualquer consulta posterior exiba seu plano detalhado de execução interna.*

### 3.2 Execução da Consulta com Análise de Rastreamento
```sql
SELECT * FROM telemetria.sensores_iot 
WHERE sensor_id = 'SENSOR-SP-001' AND data_leitura = '2026-10-24' 
LIMIT 5;
```
*O que este comando faz: Executa o SELECT e imprime, logo abaixo do resultado, a árvore de rastreamento com cada microetapa interna em microssegundos.*

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
*O que este comando faz: Desativa o rastreamento detalhado para retornar ao modo de exibição normal do terminal.*

---

## 4. Funcionamento de Forma Distribuída (Mais de uma Máquina)

### 4.1 Modos Suportados de Execução Distribuída

#### Modo A: Dois Nós em Containers Isolados (Recomendado para Apresentação - Zero Risco)
Executado na raiz do projeto com portas dedicadas e comunicação real via Gossip:
```bash
docker compose up -d --build
```
*O que este comando faz: Constrói a imagem local, sobe os nós 1 e 2 em rede interna isolada do Docker e executa a carga automática de schemas sem depender de redes externas.*

#### Modo B: Dois Computadores Físicos Reais (Laboratório / Wi-Fi / Radmin VPN)
* **Computador 1 (Máquina Seed - Nó 1):**
  ```powershell
  docker run -d --name cassandra-node1 -p 7000:7000 -p 9042:9042 -e CASSANDRA_CLUSTER_NAME="NoSQLCluster" -e CASSANDRA_DC="dc1" -e CASSANDRA_RACK="rack1" -e CASSANDRA_ENDPOINT_SNITCH="GossipingPropertyFileSnitch" -e CASSANDRA_BROADCAST_ADDRESS=IP_PC1 -e CASSANDRA_BROADCAST_RPC_ADDRESS=IP_PC1 -e CASSANDRA_SEEDS=IP_PC1 -e MAX_HEAP_SIZE="768M" -e HEAP_NEWSIZE="192M" -v ${PWD}/dados:/dados cassandra:5.0
  ```
  *O que este comando faz: Inicia o nó 1 como Seed Node no Windows, expondo a porta de Gossip 7000 e a porta CQL 9042 no IP de rede local ou Radmin.*

* **Computador 2 (Máquina Secundária - Nó 2):**
  ```bash
  python3 scripts/cluster.py
  ```
  *O que este comando faz: Executa o script interativo que detecta os IPs automaticamente, adiciona o parâmetro anti-colisão e sobe o nó 2 conectando ao PC 1.*

---

### 4.2 Verificação do Anel Distribuído (`nodetool status`)
Em qualquer uma das máquinas, execute no terminal:
```bash
docker exec -it cassandra-node1 nodetool status
```
*(ou `docker exec -it cassandra-node2 nodetool status` no Computador 2)*.

*O que este comando faz: Consulta o Gossiper interno do Cassandra e exibe a tabela de nós participantes do anel, com seus endereços IP, estado de conexão, carga e posse de tokens.*

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
   *O que este comando faz: Executa uma consulta direta no segundo computador provando que os dados inseridos no computador 1 foram sincronizados via rede pelo fator de replicação 2.*

### 4.4 Teste de Tolerância a Falhas (Alta Disponibilidade ao Vivo)
1. Com o cluster em operação, derrube propositalmente o segundo nó:
   ```bash
   docker stop cassandra-node2
   ```
   *O que este comando faz: Simula a queda abrupta de um computador/servidor do cluster.*

2. No Computador 1, consulte o status com `nodetool status`:
   * `cassandra-node1` permanece `UN` (Up / Normal).
   * `cassandra-node2` passa para `DN` (Down / Normal).

3. Execute consultas no Nó 1 sobrevivente:
   ```bash
   docker exec -it cassandra-node1 cqlsh localhost 9042 -e "SELECT * FROM telemetria.sensores_iot LIMIT 5;"
   ```
   *O que este comando faz: Comprova que o cluster continua operando e respondendo sem indisponibilidade (Zero Single Point of Failure).*

4. Religue o nó secundário:
   ```bash
   docker start cassandra-node2
   ```
   *O que este comando faz: Liga o nó novamente; o Cassandra sincroniza as mensagens pendentes (Hints) automaticamente e restabelece o anel.*

---

## 5. Limpeza do Ambiente após a Apresentação

Para desligar os containers e liberar as portas:
```bash
docker rm -f cassandra-node1 cassandra-node2
```
*O que este comando faz: Remove à força os containers criados manualmente para liberar as portas 7000 e 9042.*

*(Ou se executou via Docker Compose: `docker compose down -v`)*.
