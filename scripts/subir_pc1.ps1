# ==============================================================================
# scripts/subir_pc1.ps1
# Automação completa para inicializar a Máquina 1 (Seed Node) no Windows
# ==============================================================================

param (
    [string]$MyIP = "26.96.137.160",
    [switch]$PovoarMassa = $true
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   INICIALIZANDO CLUSTER CASSANDRA - MAQUINA 1 (SEED)     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "IP Configurado: $MyIP" -ForegroundColor Yellow

# 1. Parar container anterior se existir
Write-Host "`n[1/5] Verificando e limpando container antigo..." -ForegroundColor Yellow
docker rm -f cassandra-node1 2>$null | Out-Null
Write-Host "Container limpo com sucesso." -ForegroundColor Green

# 2. Subir container da Maquina 1
Write-Host "`n[2/5] Subindo container cassandra-node1..." -ForegroundColor Yellow
$projectDir = Resolve-Path "$PSScriptRoot\.."

docker run -d --name cassandra-node1 `
  -p 7000:7000 -p 9042:9042 `
  -e CASSANDRA_CLUSTER_NAME="NoSQLCluster" `
  -e CASSANDRA_DC="dc1" `
  -e CASSANDRA_RACK="rack1" `
  -e CASSANDRA_ENDPOINT_SNITCH="GossipingPropertyFileSnitch" `
  -e CASSANDRA_BROADCAST_ADDRESS=$MyIP `
  -e CASSANDRA_BROADCAST_RPC_ADDRESS=$MyIP `
  -e CASSANDRA_SEEDS=$MyIP `
  -e MAX_HEAP_SIZE="768M" -e HEAP_NEWSIZE="192M" `
  -v "${projectDir}\dados:/dados" `
  nosql-database-cassandra:5.0

# 3. Aguardar o Cassandra estar pronto para receber conexões CQL
Write-Host "`n[3/5] Aguardando JVM do Cassandra inicializar (leva ~35-50s)..." -ForegroundColor Yellow
$tentativas = 0
$pronto = $false

while (-not $pronto -and $tentativas -lt 30) {
    Start-Sleep -Seconds 4
    $tentativas++
    $teste = docker exec cassandra-node1 cqlsh localhost 9042 -e "SELECT cluster_name FROM system.local" 2>&1
    if ($teste -match "NoSQLCluster") {
        $pronto = $true
    } else {
        Write-Host "  -> Aguardando Cassandra responder na porta 9042... ($tentativas)" -ForegroundColor DarkGray
    }
}

if (-not $pronto) {
    Write-Host "`n[ERRO] O Cassandra demorou demais para inicializar. Verifique os logs com 'docker logs cassandra-node1'." -ForegroundColor Red
    exit 1
}

Write-Host "Cassandra esta ONLINE e pronto para receber comandos!" -ForegroundColor Green

# 4. Aplicar Schemas e Seeds
Write-Host "`n[4/5] Aplicando esquemas NoSQL (01_schema.cql e 02_seed.cql)..." -ForegroundColor Yellow
Get-Content "$projectDir\init\01_schema.cql" | docker exec -i cassandra-node1 cqlsh localhost 9042
Get-Content "$projectDir\init\02_seed.cql" | docker exec -i cassandra-node1 cqlsh localhost 9042
Write-Host "Esquemas e dados iniciais aplicados com sucesso!" -ForegroundColor Green

# 5. Povoar com massa de dados (50.000 registros)
if ($PovoarMassa) {
    Write-Host "`n[5/5] Importando grande volume de dados (50.000 registros)..." -ForegroundColor Yellow
    docker exec -i cassandra-node1 cqlsh localhost 9042 -e "COPY telemetria.sensores_iot (sensor_id, data_leitura, timestamp, temperatura, umidade, tensao_bateria, status) FROM '/dados/dados_sensores.csv' WITH HEADER = TRUE;"
    Write-Host "50.000 registros importados com sucesso!" -ForegroundColor Green
}

# 6. Exibir status final do cluster
Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "                  STATUS ATUAL DO CLUSTER                 " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
docker exec -it cassandra-node1 nodetool status

Write-Host "`nTUDO PRONTO! Para entrar no terminal CQL agora, rode:" -ForegroundColor Yellow
Write-Host "docker exec -it cassandra-node1 cqlsh localhost 9042" -ForegroundColor White
Write-Host "Ou para fazer uma consulta direta:" -ForegroundColor Yellow
Write-Host "docker exec -it cassandra-node1 cqlsh localhost 9042 -e 'USE telemetria; SELECT * FROM sensores_iot LIMIT 5;'" -ForegroundColor White

