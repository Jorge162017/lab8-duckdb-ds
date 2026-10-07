-- Vistas en memoria: los viajes permanecen en los archivos Parquet.
-- union_by_name admite columnas añadidas entre meses.
CREATE OR REPLACE VIEW yellow_raw AS
SELECT * FROM read_parquet('data/raw/yellow/*/*.parquet', union_by_name = true, filename = true);
CREATE OR REPLACE VIEW green_raw AS
SELECT * FROM read_parquet('data/raw/green/*/*.parquet', union_by_name = true, filename = true);

-- Solo se armonizan nombres; no se eliminan ni imputan registros.
CREATE OR REPLACE VIEW viajes AS
SELECT 'yellow' AS tipo_taxi, filename AS archivo,
       CAST(try_strptime(regexp_extract(filename, '_([0-9]{4}-[0-9]{2})\.parquet$', 1), '%Y-%m') AS DATE) AS mes_archivo,
       VendorID AS vendor_id, tpep_pickup_datetime AS recogida,
       tpep_dropoff_datetime AS llegada, passenger_count, trip_distance,
       RatecodeID AS ratecode_id, store_and_fwd_flag,
       PULocationID AS zona_origen, DOLocationID AS zona_destino,
       payment_type, fare_amount, extra, mta_tax, tip_amount, tolls_amount,
       improvement_surcharge, total_amount, congestion_surcharge,
       Airport_fee AS airport_fee, cbd_congestion_fee, request_source,
       NULL::DOUBLE AS ehail_fee, NULL::BIGINT AS trip_type
FROM yellow_raw
UNION ALL
SELECT 'green', filename,
       CAST(try_strptime(regexp_extract(filename, '_([0-9]{4}-[0-9]{2})\.parquet$', 1), '%Y-%m') AS DATE),
       VendorID, lpep_pickup_datetime, lpep_dropoff_datetime,
       passenger_count, trip_distance, RatecodeID, store_and_fwd_flag,
       PULocationID, DOLocationID, payment_type, fare_amount, extra, mta_tax,
       tip_amount, tolls_amount, improvement_surcharge, total_amount,
       congestion_surcharge, NULL::DOUBLE, cbd_congestion_fee,
       request_source, ehail_fee, trip_type
FROM green_raw;
