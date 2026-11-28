-- =====================================================================
-- Dimensión FACT_VIVIENDA
-- =====================================================================

DROP TABLE IF EXISTS fact_vivienda;

CREATE TABLE fact_vivienda (
    cod_municipio INT   NOT NULL,
    periodo INT         NOT NULL,

    -- Demografía y hogares
    poblacion INT,
    poblacion_extranjera INT,
    porcentaje_poblacion_extranjera DECIMAL(6,3),
    num_total_hogares INT,
    proporcion_viviendas_vacias DECIMAL(6,3),
    porcentaje_viviendas_turisticas DECIMAL(6,3),
    porcentaje_hogares_unipersonales DECIMAL(6,3),
    num_centros_sanitarios INT,

    -- Indicadores de alquiler
    alquiler_medio_anual DECIMAL(9,3),
    primer_cuartil_alquiler_mensual DECIMAL(7,3),
    mediana_alquiler_mensual DECIMAL(9,3),
    tercer_cuartil_alquiler_mensual DECIMAL(9,3),
    dispersion_alquiler_mensual DECIMAL(9,3),
    dispersion_relativa_alquiler DECIMAL(9,3),
    indice_ipva DECIMAL(5,2),

    -- Indicadores de compra y rentabilidad
    precio_medio_vivienda DECIMAL(12,3),
    precio_medio_vivienda_piso DECIMAL(12,3),
    precio_medio_vivienda_unifamiliar DECIMAL(12,3),
    ratio_precio_alquiler DECIMAL(9,3),
    rentabilidad_bruta_alquiler DECIMAL(6,3),

    -- Socioeconómicos y seguridad
    total_infracciones_penales DECIMAL(4,2),
    tasa_desempleo DECIMAL(6,3),
    tasa_empleo DECIMAL(6,3),
    tasa_actividad_economica DECIMAL(5,2),
    renta_media_anual_hogar DECIMAL(13,3),
    esfuerzo FLOAT,
    
    CONSTRAINT pk_region PRIMARY KEY (cod_municipio, periodo),
    -- Declaración de claves ajenas
    CONSTRAINT fk_vivienda_region FOREIGN KEY (cod_municipio) 
        REFERENCES dim_municipio (cod_municipio),
        
    CONSTRAINT fk_vivienda_fecha FOREIGN KEY (periodo) 
        REFERENCES fecha (periodo)
);