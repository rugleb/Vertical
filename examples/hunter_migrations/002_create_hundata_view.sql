CREATE MATERIALIZED VIEW hundata AS SELECT * FROM submissions;

CREATE INDEX hundata_phk1_index ON hundata (phk1);
