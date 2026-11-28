-- =====================================================================
-- Dimensión REGION del Data Warehouse
-- Jerarquía geográfica: municipio -> provincia -> comunidad autónoma
-- =====================================================================

DROP TABLE IF EXISTS dim_ccaa;
DROP TABLE IF EXISTS dim_provincia;
DROP TABLE IF EXISTS dim_municipio;

-- 1. Nivel Superior: CCAA (Aquí residen los flags fiscales)
CREATE TABLE dim_ccaa (
    cod_ccaa        SMALLINT     NOT NULL,
    ccaa            VARCHAR(30)  NOT NULL,
    regimen_comun   BOOLEAN      NOT NULL,
    regimen_foral   BOOLEAN      NOT NULL,

    CONSTRAINT pk_dim_ccaa PRIMARY KEY (cod_ccaa),
    CONSTRAINT ck_ccaa_regimen CHECK (regimen_comun <> regimen_foral)
);

-- 2. Nivel Intermedio: Provincia (Apunta a CCAA)
CREATE TABLE dim_provincia (
    cod_provincia   SMALLINT     NOT NULL,
    provincia       VARCHAR(25)  NOT NULL,
    cod_ccaa        SMALLINT     NOT NULL,

    CONSTRAINT pk_dim_provincia PRIMARY KEY (cod_provincia),
    CONSTRAINT fk_provincia_ccaa FOREIGN KEY (cod_ccaa) 
        REFERENCES dim_ccaa(cod_ccaa)
);

-- 3. Nivel Base / Grano: Municipio (Apunta a Provincia)
CREATE TABLE dim_municipio (
    cod_municipio   SMALLINT     NOT NULL,
    municipio       VARCHAR(50)  NOT NULL,
    cod_provincia   SMALLINT     NOT NULL,

    CONSTRAINT pk_dim_municipio PRIMARY KEY (cod_municipio),
    CONSTRAINT fk_municipio_provincia FOREIGN KEY (cod_provincia) 
        REFERENCES dim_provincia(cod_provincia),
    CONSTRAINT ck_municipio_id CHECK (cod_municipio BETWEEN 0 AND 9999)
);
