-- =====================================================================
-- Dimensión REGION del Data Warehouse
-- Jerarquía geográfica: municipio -> provincia -> comunidad autónoma
-- =====================================================================

DROP TABLE IF EXISTS region;

CREATE TABLE region (
    cod_municipio   SMALLINT     NOT NULL,   -- código de 4 dígitos
    municipio       VARCHAR(50)  NOT NULL,   -- máx. real: "Villarcayo de Merindad de Castilla la Vieja" (43)
    cod_provincia   SMALLINT     NOT NULL,   -- código de 2 dígitos
    provincia       VARCHAR(25)  NOT NULL,   -- máx. real: "Santa Cruz de Tenerife" (22)
    cod_ccaa        SMALLINT     NOT NULL,   -- código de 2 dígitos
    ccaa            VARCHAR(30)  NOT NULL,   -- máx. real: "Navarra, Comunidad Foral de" (27)
    regimen_comun   BOOLEAN      NOT NULL,
    regimen_foral   BOOLEAN      NOT NULL,

    -- validación
    CONSTRAINT pk_region PRIMARY KEY (cod_municipio),
    CONSTRAINT ck_region_cod_municipio CHECK (cod_municipio BETWEEN 0 AND 9999),
    CONSTRAINT ck_region_cod_provincia CHECK (cod_provincia BETWEEN 0 AND 99),
    CONSTRAINT ck_region_cod_ccaa      CHECK (cod_ccaa      BETWEEN 0 AND 99),
    -- Un municipio pertenece a un único régimen fiscal
    CONSTRAINT ck_region_regimen       CHECK (regimen_comun <> regimen_foral)
);
