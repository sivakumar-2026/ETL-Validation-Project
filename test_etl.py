import pandas as pd


def test_row_count_validation(get_data):
    """TEST: Check if Source and Target row counts match"""
    df_src, df_tgt = get_data
    src_cnt = len(df_src)
    tgt_cnt = len(df_tgt)

    assert src_cnt == tgt_cnt, f"❌ Count Mismatch! Source: {src_cnt}, Target: {tgt_cnt}"


def test_schema_validation(get_data):
    """TEST: Check if all column names match between systems"""
    df_src, df_tgt = get_data
    src_cols = set(df_src.columns)
    tgt_cols = set(df_tgt.columns)

    assert src_cols == tgt_cols, f"❌ Column Mismatch! Missing: {src_cols - tgt_cols}"


def test_data_reconciliation(get_data):
    """TEST: Compare actual data values (Cell-by-Cell)"""
    df_src, df_tgt = get_data

    df_src_sorted = df_src.sort_values("ALBUMID").reset_index(drop=True)
    df_tgt_sorted = df_tgt.sort_values("ALBUMID").reset_index(drop=True)

    pd.testing.assert_frame_equal(df_src_sorted, df_tgt_sorted)


def test_data_quality_nulls(get_data):
    """TEST: Ensure mandatory columns (TITLE) have no NULL values in Target"""
    _, df_tgt = get_data
    null_count = df_tgt["TITLE"].isnull().sum()

    assert null_count == 0, f"❌ Data Quality Issue: Found {null_count} NULLs in Target Table!"
