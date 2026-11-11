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

1. **Interface Administrativa do Nó (`nodetool`):**
   ```bash
   docker exec -it cassandra-node2 nodetool info
   ```
   *O que este comando faz: Exibe métricas de infraestrutura do nó, como tempo em atividade (uptime), uso de memória heap da JVM, ID do host e taxas de carga.*

### 1.3 Verificação do Anel Distribuído (`nodetool status`)
Em qualquer uma das máquinas, execute no terminal:
```bash
docker exec -it cassandra-node2 nodetool status
```

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

3. **Interface Gráfica Visual (Extensão CQL no VS Code / DBeaver):**
   Conexão JDBC/CQL configurada em `localhost:9042` com os Keyspaces `telemetria` e `app`, permitindo navegação estrutural das tabelas e execução visual de scripts.

---

## 2. Esquema Simples de Armazenamento e Consulta de Dados

Acesse o terminal do Cassandra:
```bash
docker exec -it cassandra-node2 cqlsh localhost 9042
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

### 2.3 Listar as Diferentes Classes de Sensores no Banco
Para visualizar os diferentes sensores (e suas respectivas datas particionadas) armazenados na tabela:
```sql
SELECT DISTINCT sensor_id, data_leitura FROM telemetria.sensores_iot;
```
*O que este comando faz: Lista as chaves de partição distintas existentes no cluster. Como a chave de partição é composta por `(sensor_id, data_leitura)`, o Cassandra exige que ambas as colunas sejam solicitadas no `SELECT DISTINCT` para identificar as diferentes classes de sensores sem precisar ler todas as linhas de dados.*

### 2.4 Criar / Inserir uma Nova Classe de Sensor
Para criar uma nova classe de sensor (ou registrar uma nova medição ao vivo durante a demonstração):
```sql
INSERT INTO telemetria.sensores_iot (sensor_id, data_leitura, timestamp, temperatura, umidade, tensao_bateria, status)
VALUES ('SENSOR-DEMO-01', '2026-10-26', toTimestamp(now()), 28.4, 58.0, 3.85, 'NORMAL');
```
*O que este comando faz: Insere um novo registro no cluster criando automaticamente a nova partição `('SENSOR-DEMO-01', '2026-10-26')` caso ela ainda não exista. No Cassandra, o `INSERT` funciona como um `UPSERT`: ele grava diretamente no CommitLog sequencial e na MemTable em memória RAM, sendo replicado em tempo real para o segundo nó sem precisar criar um catálogo prévio de sensores.*

### 2.5 Apagar Todos os Registros de uma Classe Específica de Sensor
Para deletar todas as leituras de um sensor específico (ex: `SALA-SERVIDORES-CORE` ou `SENSOR-SP-001`):
```sql
DELETE FROM telemetria.sensores_iot 
WHERE sensor_id = 'SALA-SERVIDORES-CORE' 
  AND data_leitura IN ('2026-10-24', '2026-10-25', '2026-10-26');
```
*O que este comando faz: Remove todas as linhas pertencentes à classe de sensor informada nos dias registrados. O Cassandra exige todas as colunas da chave de partição no `WHERE` (por isso passamos `sensor_id` e a lista de datas em `data_leitura IN`). Internamente, em vez de apagar na hora do disco, ele grava marcadores chamados **Tombstones** (lápides) para que a exclusão definitiva ocorra na compactação em segundo plano.*

*(Para confirmar que foi apagado, execute: `SELECT COUNT(*) FROM telemetria.sensores_iot WHERE sensor_id = 'SALA-SERVIDORES-CORE' AND data_leitura IN ('2026-10-24', '2026-10-25', '2026-10-26');`)*

### Passo 2.6: Comprovação do Volume na Tabela
No terminal `cqlsh`:
```sql
SELECT COUNT(*) FROM telemetria.sensores_iot;
```
*O que este comando faz: Realiza a contagem agregada de registros no cluster para comprovar que os 50.000 dados estão armazenados.*

---


### Passo 3: Consulta Otimizada por Partição com Alto Volume
Demonstração de busca pontual de alta performance mesmo com 50.000 registros:
```sql
SELECT sensor_id, data_leitura, timestamp, temperatura, umidade, status 
FROM telemetria.sensores_iot 
WHERE sensor_id = 'SENSOR-SP-001' AND data_leitura = '2026-10-24' 
LIMIT 5;
```
*O que este comando faz: Busca registros filtrando diretamente pela Chave de Partição exata. O Cassandra calcula o token hash e vai direto no local físico correto sem fazer varredura desnecessária.*

---



## 3. Teste de Tolerância a Falhas (Alta Disponibilidade ao Vivo)



### 3.1 Teste de Tolerância a Falhas (Alta Disponibilidade ao Vivo)
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

## 4. Limpeza do Ambiente após a Apresentação

Para desligar os containers e liberar as portas:
```bash
docker rm -f cassandra-node1 cassandra-node2
```
*O que este comando faz: Remove à força os containers criados manualmente para liberar as portas 7000 e 9042.*

*(Ou se executou via Docker Compose: `docker compose down -v`)*.
