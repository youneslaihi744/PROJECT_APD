-- =====================================================================
-- Dimensión FECHA del Data Warehouse
-- =====================================================================

DROP TABLE IF EXISTS fecha;

CREATE TABLE fecha(
    periodo         SMALLINT    NOT NULL,
    covid           BOOLEAN     NOT NULL,
    ley_vivienda    BOOLEAN     NOT NULL,
    
    CONSTRAINT pk_fecha PRIMARY KEY (periodo),
    CONSTRAINT is_a_year CHECK (periodo BETWEEN 2010 AND 2026)
);
