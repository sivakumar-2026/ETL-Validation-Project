"""PySpark JDBC validations: MSSQL source vs Postgres target."""

from pyspark.sql import functions as F

from conftest import PRIMARY_KEY


class TestSparkRowCounts:
    def test_spark_row_counts_match(self, spark_frames):
        df_src, df_tgt = spark_frames
        src_cnt = df_src.count()
        tgt_cnt = df_tgt.count()
        assert src_cnt == tgt_cnt, (
            f"Spark count mismatch: source={src_cnt}, target={tgt_cnt}"
        )

    def test_spark_target_not_empty(self, spark_frames):
        _, df_tgt = spark_frames
        assert df_tgt.count() > 0, "Target Spark DataFrame is empty"


class TestSparkKeys:
    def test_no_duplicate_keys_in_target(self, spark_frames):
        _, df_tgt = spark_frames
        dupes = (
            df_tgt.groupBy(PRIMARY_KEY)
            .count()
            .filter(F.col("count") > 1)
            .count()
        )
        assert dupes == 0, f"Found {dupes} duplicate {PRIMARY_KEY} groups in target"

    def test_key_sets_match(self, spark_frames):
        df_src, df_tgt = spark_frames
        only_src = df_src.select(PRIMARY_KEY).subtract(df_tgt.select(PRIMARY_KEY)).count()
        only_tgt = df_tgt.select(PRIMARY_KEY).subtract(df_src.select(PRIMARY_KEY)).count()
        assert only_src == 0, f"{only_src} keys only in source"
        assert only_tgt == 0, f"{only_tgt} keys only in target"


class TestSparkValueMatch:
    COMPARE_COLS = [
        "ALBUMID",
        "TITLE",
        "ARTISTID",
    ]

    def test_joined_rows_have_no_mismatches(self, spark_frames):
        df_src, df_tgt = spark_frames

        src = df_src.select(*[F.col(c).alias(f"S_{c}") for c in self.COMPARE_COLS])
        tgt = df_tgt.select(*[F.col(c).alias(f"T_{c}") for c in self.COMPARE_COLS])

        joined = src.join(tgt, src[f"S_{PRIMARY_KEY}"] == tgt[f"T_{PRIMARY_KEY}"], "inner")

        mismatch_expr = None
        for col in self.COMPARE_COLS:
            if col == PRIMARY_KEY:
                continue
            # rating: allow tiny float drift; timestamps: compare as strings
            cond = F.col(f"S_{col}") != F.col(f"T_{col}")
            mismatch_expr = cond if mismatch_expr is None else (mismatch_expr | cond)

        bad = joined.filter(mismatch_expr)
        bad_count = bad.count()
        sample = [row.asDict() for row in bad.limit(5).collect()] if bad_count else []

        assert bad_count == 0, (
            f"{bad_count} value mismatches on join key {PRIMARY_KEY}. Sample: {sample}"
        )

    def test_max_albumid_matches(self, spark_frames):
        df_src, df_tgt = spark_frames
        src_max = df_src.agg(F.max("ALBUMID").alias("m")).collect()[0]["m"]
        tgt_max = df_tgt.agg(F.max("ALBUMID").alias("m")).collect()[0]["m"]
        assert src_max == tgt_max, (
            f"Max ALBUMID mismatch: source={src_max}, target={tgt_max}"
        )
