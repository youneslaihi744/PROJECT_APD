-- =====================================================================
-- Dimensión FACT_VIVIENDA
-- =====================================================================

DROP TABLE IF EXISTS fact_vivienda_ccaa;

CREATE TABLE fact_vivienda_ccaa (
    cod_ccaa INT NOT NULL,
    periodo INT   NOT NULL,
    indice_ipv DECIMAL(6,3),
    Salario_medio DECIMAL(6,3) ,
    viviendas_terminadas INT , 
    saldo_total INT , 
    ratio_viviendas_saldo DECIMAL(6,3) ,

  
    CONSTRAINT pk_region PRIMARY KEY (cod_ccaa, periodo),
    -- Declaración de claves ajenas
    CONSTRAINT fk_vivienda_comunidad_autonoma FOREIGN KEY (cod_ccaa) 
        REFERENCES dim_ccaa (cod_ccaa),
        
    CONSTRAINT fk_vivienda_fecha FOREIGN KEY (periodo) 
        REFERENCES fecha (periodo)
);