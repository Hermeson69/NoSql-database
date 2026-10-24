-- ==============================================================================
-- 02_seed.cql
-- Dados de teste iniciais para validação rápida do cluster
-- ==============================================================================

USE telemetria;

INSERT INTO sensores_iot (sensor_id, data_leitura, timestamp, temperatura, umidade, tensao_bateria, status)
VALUES ('SENSOR-SP-001', '2026-10-24', '2026-10-24 14:00:00+0000', 24.5, 62.1, 3.78, 'NORMAL');

INSERT INTO sensores_iot (sensor_id, data_leitura, timestamp, temperatura, umidade, tensao_bateria, status)
VALUES ('SENSOR-SP-001', '2026-10-24', '2026-10-24 14:05:00+0000', 25.1, 61.8, 3.77, 'NORMAL');

INSERT INTO sensores_iot (sensor_id, data_leitura, timestamp, temperatura, umidade, tensao_bateria, status)
VALUES ('SENSOR-RJ-002', '2026-10-24', '2026-10-24 14:00:00+0000', 31.8, 75.4, 3.65, 'ALERTA');

USE app;

INSERT INTO users (id, public_id, name, email, created_at)
VALUES (1, uuid(), 'Hermeson', 'hermeson@email.com', toTimestamp(now()));
