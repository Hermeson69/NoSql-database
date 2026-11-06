# ==============================================================================
# scripts/subir_pc2.ps1
# Automacao para inicializar a Maquina 2 (Secundaria) no WINDOWS (PowerShell)
# ==============================================================================

param (
    [string]$SeedIP = "26.96.137.160",
    [string]$MyIP = "26.42.12.45"
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   INICIALIZANDO CLUSTER CASSANDRA - MAQUINA 2 (WINDOWS)  " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "IP do Seed (PC 1): $SeedIP" -ForegroundColor Yellow
Write-Host "IP desta Maquina (PC 2): $MyIP" -ForegroundColor Yellow

# 1. Limpar container anterior se existir
Write-Host "`n[1/3] Limpando container antigo..." -ForegroundColor Yellow
docker rm -f cassandra-node2 2>$null | Out-Null
Write-Host "Container limpo com sucesso." -ForegroundColor Green

# 2. Subir container da Maquina 2
Write-Host "`n[2/3] Subindo container cassandra-node2..." -ForegroundColor Yellow
docker run -d --name cassandra-node2 `
  -p 7000:7000 -p 9042:9042 `
  -e CASSANDRA_CLUSTER_NAME="NoSQLCluster" `
  -e CASSANDRA_DC="dc1" `
  -e CASSANDRA_RACK="rack1" `
  -e CASSANDRA_ENDPOINT_SNITCH="GossipingPropertyFileSnitch" `
  -e CASSANDRA_BROADCAST_ADDRESS=$MyIP `
  -e CASSANDRA_BROADCAST_RPC_ADDRESS=$MyIP `
  -e CASSANDRA_SEEDS=$SeedIP `
  -e MAX_HEAP_SIZE="768M" -e HEAP_NEWSIZE="192M" `
  cassandra:5.0

# 3. Aguardar o Cassandra se juntar ao cluster
Write-Host "`n[3/3] Aguardando o Cassandra se juntar ao anel (~35-50s)..." -ForegroundColor Yellow
$tentativas = 0
$pronto = $false

while (-not $pronto -and $tentativas -lt 30) {
    Start-Sleep -Seconds 4
    $tentativas++
    $teste = docker exec cassandra-node2 cqlsh localhost 9042 -e "SELECT cluster_name FROM system.local" 2>&1
    if ($teste -match "NoSQLCluster") {
        $pronto = $true
    } else {
        Write-Host "  -> Aguardando sincronizacao do anel... ($tentativas)" -ForegroundColor DarkGray
    }
}

if (-not $pronto) {
    Write-Host "`n[ERRO] O Cassandra demorou demais para inicializar. Verifique os logs com 'docker logs cassandra-node2'." -ForegroundColor Red
    exit 1
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "                  STATUS ATUAL DO CLUSTER                 " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
docker exec -it cassandra-node2 nodetool status

Write-Host "`nTUDO PRONTO NO PC 2! Para consultar a tabela replicada:" -ForegroundColor Yellow
Write-Host "docker exec -it cassandra-node2 cqlsh localhost 9042 -e 'USE telemetria; SELECT * FROM sensores_iot LIMIT 5;'" -ForegroundColor White

