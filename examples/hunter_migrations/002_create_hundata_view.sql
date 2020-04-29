CREATE MATERIALIZED VIEW yavert.hundata AS SELECT * FROM yavert.submissions;

CREATE INDEX hundata_phk1_index ON yavert.hundata (phk1);
