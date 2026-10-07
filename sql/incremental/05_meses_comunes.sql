-- Define cobertura comparable. No compara un año completo con uno parcial.
WITH cobertura AS (
    SELECT year(mes_archivo) AS anio, month(mes_archivo) AS mes,
           count(DISTINCT tipo_taxi) AS tipos
    FROM viajes WHERE year(mes_archivo) IN (2024, 2026)
    GROUP BY anio, mes
), comunes AS (
    SELECT mes FROM cobertura WHERE tipos = 2 GROUP BY mes HAVING count(DISTINCT anio) = 2
)
SELECT c.anio, c.mes, c.tipos
FROM cobertura c JOIN comunes USING (mes)
ORDER BY c.anio, c.mes;
