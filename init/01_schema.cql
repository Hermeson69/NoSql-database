-- ==============================================================================
-- 01_schema.cql
-- Esquema NoSQL para o Apache Cassandra (Cluster Distribuído)
-- Fator de Replicação: 2 (distribuído entre cassandra-node1 e cassandra-node2)
-- ==============================================================================

-- 1. Criação do Usuário/Role root (para compatibilidade com ferramentas visuais e README):
-- Executado com segurança caso PasswordAuthenticator esteja ativo
CREATE ROLE IF NOT EXISTS root WITH PASSWORD = 'root' AND SUPERUSER = true AND LOGIN = true;

-- 2. Criação do Keyspace de Telemetria com Replicação em 2 nós:
CREATE KEYSPACE IF NOT EXISTS telemetria 
WITH replication = {
    'class': 'SimpleStrategy', 
    'replication_factor': 2
};

-- 2. Tabela Principal de Modelagem NoSQL Real (Série Temporal de IoT)
-- Chave de Partição: (sensor_id, data_leitura) -> Espalha os dados pelos nós
-- Chave de Clusterização: timestamp DESC -> Ordena fisicamente no disco em ordem cronológica
CREATE TABLE IF NOT EXISTS telemetria.sensores_iot (
    sensor_id text,
    data_leitura date,
    timestamp timestamp,
    temperatura double,
    umidade double,
    tensao_bateria double,
    status text,
    PRIMARY KEY ((sensor_id, data_leitura), timestamp)
) WITH CLUSTERING ORDER BY (timestamp DESC)
  AND comment = 'Tabela de telemetria otimizada para consultas por sensor e dia';

-- 3. Keyspace e Tabela legada para compatibilidade de testes simples:
CREATE KEYSPACE IF NOT EXISTS app 
WITH replication = {
    'class': 'SimpleStrategy', 
    'replication_factor': 2
};

CREATE TABLE IF NOT EXISTS app.users (
    id int PRIMARY KEY,
    public_id uuid,
    name text,
    email text,
    created_at timestamp
);
