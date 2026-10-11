"""Pytest automation for ETL count validations."""

import pytest

from conftest import PRIMARY_KEY, TGT_TABLE


class TestRowCounts:
    """Validate row counts between source and target."""

    def test_source_target_sql_count_match(self, table_counts):
        src_cnt = table_counts["source"]
        tgt_cnt = table_counts["target"]

        assert src_cnt == tgt_cnt, (
            f"Count mismatch: source={src_cnt}, target={tgt_cnt}"
        )

    def test_source_target_dataframe_count_match(self, get_data):
        df_src, df_tgt = get_data

        assert len(df_src) == len(df_tgt), (
            f"DataFrame count mismatch: source={len(df_src)}, target={len(df_tgt)}"
        )

    def test_target_table_not_empty(self, table_counts):
        assert table_counts["target"] > 0, "Target table is empty"


class TestDistinctCounts:
    """Validate distinct key counts."""

    def test_distinct_primary_key_count_match(self, get_data):
        df_src, df_tgt = get_data

        src_distinct = df_src[PRIMARY_KEY].nunique()
        tgt_distinct = df_tgt[PRIMARY_KEY].nunique()

        assert src_distinct == tgt_distinct, (
            f"Distinct {PRIMARY_KEY} mismatch: "
            f"source={src_distinct}, target={tgt_distinct}"
        )

    def test_primary_key_count_equals_row_count(self, get_data):
        """Each row should have a unique primary key in both systems."""
        _, df_tgt = get_data

        row_count = len(df_tgt)
        distinct_count = df_tgt[PRIMARY_KEY].nunique()

        assert row_count == distinct_count, (
            f"Duplicate {PRIMARY_KEY} values in target: "
            f"rows={row_count}, distinct={distinct_count}"
        )


class TestDuplicateCounts:
    """Validate duplicate row counts."""

    def test_no_full_row_duplicates_in_target(self, get_data):
        _, df_tgt = get_data

        duplicate_count = df_tgt.duplicated().sum()

        assert duplicate_count == 0, (
            f"Found {duplicate_count} duplicate rows in {TGT_TABLE}"
        )

class TestNullCounts:
    """Validate null counts in target data."""

    MANDATORY_COLUMNS = ["ALBUMID", "TITLE", "ARTISTID"]

    @pytest.mark.parametrize("column", MANDATORY_COLUMNS)
    def test_mandatory_columns_have_no_nulls(self, get_data, column):
        _, df_tgt = get_data

        null_count = df_tgt[column].isnull().sum()

        assert null_count == 0, (
            f"Found {null_count} NULL values in mandatory column {column}"
        )

    def test_null_count_summary(self, get_data):
        """Report null counts for all columns; fail if any mandatory column has nulls."""
        _, df_tgt = get_data

        null_counts = df_tgt.isnull().sum().to_dict()
        failing_columns = {
            col: count
            for col, count in null_counts.items()
            if count > 0 and col in self.MANDATORY_COLUMNS
        }

        assert not failing_columns, f"Null counts in mandatory columns: {failing_columns}"


class TestRecordDiffCounts:
    """Validate record-level difference counts."""

    def test_records_only_in_source(self, get_data):
        df_src, df_tgt = get_data

        src_keys = set(df_src[PRIMARY_KEY])
        tgt_keys = set(df_tgt[PRIMARY_KEY])
        only_in_source = src_keys - tgt_keys

        assert len(only_in_source) == 0, (
            f"{len(only_in_source)} records exist in source but not in target: "
            f"{sorted(only_in_source)[:10]}"
        )

    def test_records_only_in_target(self, get_data):
        df_src, df_tgt = get_data

        src_keys = set(df_src[PRIMARY_KEY])
        tgt_keys = set(df_tgt[PRIMARY_KEY])
        only_in_target = tgt_keys - src_keys

        assert len(only_in_target) == 0, (
            f"{len(only_in_target)} records exist in target but not in source: "
            f"{sorted(only_in_target)[:10]}"
        )

    def test_sql_count_matches_dataframe_count(self, get_data, table_counts):
        _, df_tgt = get_data

        sql_tgt_count = table_counts["target"]
        df_tgt_count = len(df_tgt)

        assert sql_tgt_count == df_tgt_count, (
            f"SQL count ({sql_tgt_count}) does not match DataFrame count ({df_tgt_count})"
        )
