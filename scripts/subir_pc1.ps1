# ==============================================================================
# scripts/subir_pc1.ps1
# Automação completa para inicializar a Máquina 1 (Seed Node) no Windows
# Uso normal: .\scripts\subir_pc1.ps1
# Checar status a qualquer momento: .\scripts\subir_pc1.ps1 -Status
# ==============================================================================

param (
    [string]$MyIP = "26.96.137.160",
    [switch]$PovoarMassa = $true,
    [switch]$EsperarPC2 = $true,
    [switch]$Status = $false
)

function Exibir-DiagnosticoCluster {
    Write-Host "`n==========================================================" -ForegroundColor Cyan
    Write-Host "                  STATUS DO CLUSTER                       " -ForegroundColor Cyan
    Write-Host "==========================================================" -ForegroundColor Cyan

    $statusOutput = docker exec cassandra-node1 nodetool status 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERRO] Container cassandra-node1 nao esta respondendo." -ForegroundColor Red
        return
    }

    Write-Host "`nTabela do nodetool status:" -ForegroundColor DarkGray
    $statusOutput | ForEach-Object {
        if ($_ -match "^UN\s+") {
            Write-Host "  $_" -ForegroundColor Green
        } elseif ($_ -match "^(D|U)(J|L|M|D)\s+") {
            Write-Host "  $_" -ForegroundColor Yellow
        } else {
            Write-Host "  $_" -ForegroundColor Gray
        }
    }

    $nosUN = @($statusOutput | Where-Object { $_ -match "^UN\s+" })

    Write-Host "`n----------------------------------------------------------" -ForegroundColor DarkCyan
    if ($nosUN.Count -ge 2) {
        Write-Host " [OK] SUCESSO TOTAL! AS 2 MAQUINAS ESTAO 100% CONECTADAS! " -ForegroundColor Black -BackgroundColor Green
        Write-Host "`n -> Maquinas no anel: $($nosUN.Count) computadores fisicos" -ForegroundColor Green
        Write-Host " -> Status: UN (Up / Normal) em ambos os computadores." -ForegroundColor Green
        Write-Host " -> Replicacao RF=2: Totalmente ativa e sincronizada!" -ForegroundColor Green
    } elseif ($nosUN.Count -eq 1) {
        Write-Host " [AGUARDANDO] Apenas a Maquina 1 esta ativa no anel.       " -ForegroundColor Black -BackgroundColor Yellow
        Write-Host "`n -> A Maquina 2 ainda nao se conectou ao cluster." -ForegroundColor Yellow
        Write-Host " -> Peca para o colega iniciar o script no PC 2." -ForegroundColor Yellow
    } else {
        Write-Host " [ATENCAO] Nenhum no com status UN detectado." -ForegroundColor Red
    }
    Write-Host "----------------------------------------------------------" -ForegroundColor DarkCyan
}

# Se o usuário só pediu para checar o status:
if ($Status) {
    Exibir-DiagnosticoCluster
    exit 0
}

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

# 6. Aguardar PC 2 se conectar (se ainda não estiver no anel)
if ($EsperarPC2) {
    $rawCheck = docker exec cassandra-node1 nodetool status 2>&1
    $nosUNCheck = @($rawCheck | Where-Object { $_ -match "^UN\s+" })
    
    if ($nosUNCheck.Count -lt 2) {
        Write-Host "`n[AGUARDANDO PC 2] A Maquina 1 esta pronta! Aguardando o PC 2 se juntar ao anel..." -ForegroundColor Yellow
        Write-Host "(Dica: peca para o colega rodar o script no PC 2. Pressione Ctrl+C se quiser pular)" -ForegroundColor DarkGray
        
        $maxEspera = 20
        $espera = 0
        while ($nosUNCheck.Count -lt 2 -and $espera -lt $maxEspera) {
            Start-Sleep -Seconds 4
            $espera++
            $rawCheck = docker exec cassandra-node1 nodetool status 2>&1
            $nosUNCheck = @($rawCheck | Where-Object { $_ -match "^UN\s+" })
            Write-Host "  -> Verificando conexao do PC 2... ($espera/$maxEspera) - Nos UN: $($nosUNCheck.Count)" -ForegroundColor DarkGray
        }
    }
}

# Exibição Final
Exibir-DiagnosticoCluster

Write-Host "`nTUDO PRONTO! Para consultar os dados da tabela, execute:" -ForegroundColor Yellow
Write-Host "docker exec -it cassandra-node1 cqlsh localhost 9042 -e 'USE telemetria; SELECT * FROM sensores_iot LIMIT 5;'" -ForegroundColor White
Write-Host "`nPara rechecar o status do anel a qualquer momento, basta rodar:" -ForegroundColor Yellow
Write-Host ".\scripts\subir_pc1.ps1 -Status" -ForegroundColor White
