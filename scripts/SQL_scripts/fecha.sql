-- =====================================================================
-- Dimensión FECHA del Data Warehouse
-- =====================================================================

DROP TABLE IF EXISTS fecha;

CREATE TABLE fecha(
    periodo SMALLINT,

    CONSTRAINT pk_fecha PRIMARY KEY (periodo),
    CONSTRAINT is_a_year CHECK (periodo BETWEEN 2010 AND 2026)
);
