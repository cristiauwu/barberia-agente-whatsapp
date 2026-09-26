-- Purga definitiva de la clave del vendedor.
--
-- DIAGNOSTICO: la busqueda en la columna `data` da 0, pero la clave SI esta
-- en la columna `workflowData` (json), que guarda una copia del workflow tal
-- como estaba cuando se ejecuto. Las 94 ejecuciones son del bucle de 518 y
-- de las pruebas, sin valor operativo.

\echo '=== ANTES: donde esta exactamente ==='
SELECT 'data' AS columna, count(*) AS filas
FROM execution_data WHERE data LIKE '%CLAVE_DEL_PROVEEDOR%'
UNION ALL
SELECT 'workflowData', count(*)
FROM execution_data WHERE "workflowData"::text LIKE '%CLAVE_DEL_PROVEEDOR%';

\echo '=== Borrando las ejecuciones afectadas ==='
DELETE FROM execution_data
WHERE "workflowData"::text LIKE '%CLAVE_DEL_PROVEEDOR%'
   OR data LIKE '%CLAVE_DEL_PROVEEDOR%';

\echo '=== Borrando sus cabeceras huerfanas ==='
DELETE FROM execution_entity e
WHERE NOT EXISTS (
    SELECT 1 FROM execution_data d WHERE d."executionId" = e.id
);

\echo '=== DESPUES: la clave en execution_data ==='
SELECT count(*) AS filas_con_clave
FROM execution_data WHERE "workflowData"::text LIKE '%CLAVE_DEL_PROVEEDOR%';

\echo '=== Totales restantes ==='
SELECT count(*) AS ejecuciones_restantes FROM execution_entity;

\echo '=== La clave en el resto de tablas de n8n ==='
SELECT 'workflow_entity' AS tabla, count(*) AS filas
FROM workflow_entity WHERE nodes::text LIKE '%CLAVE_DEL_PROVEEDOR%'
UNION ALL
SELECT 'workflow_history', count(*)
FROM workflow_history WHERE nodes::text LIKE '%CLAVE_DEL_PROVEEDOR%';