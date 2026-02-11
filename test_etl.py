import pytest
import pandas as pd
from sqlalchemy import create_engine
import urllib.parse

# ---------------------------------------------------------
# 1. DATABASE ENGINES SETUP
# ---------------------------------------------------------

# SOURCE: SQL Server (On-Premise) - Using TestDB
mssql_params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost,1433;"
    "DATABASE=TestDB;"
    "UID=sa;"
    "PWD=Filmmaker@2024;"
    "TrustServerCertificate=yes;"
)
src_engine = create_engine(f"mssql+pyodbc:///?odbc_connect={mssql_params}")

# TARGET: Postgres (Docker) - Encoding password to handle the '@' symbol
pg_pass = urllib.parse.quote_plus("Tester@2024")
tgt_engine = create_engine(f"postgresql+psycopg2://postgres:{pg_pass}@localhost:5432/postgres")

# ---------------------------------------------------------
# 2. PYTEST FIXTURES (Data Extraction)
# ---------------------------------------------------------

@pytest.fixture(scope="module")
def get_data():
    """Extracts data from both Source and Target for comparison"""
    # Using 'dbo' schema for SQL Server and 'public' for Postgres
    df_src = pd.read_sql("SELECT * FROM dbo.Movies", src_engine)
    df_tgt = pd.read_sql("SELECT * FROM public.Movies", tgt_engine)
    
    # ETL Best Practice: Standardize column names to UPPERCASE 
    # This prevents failures caused by Postgres defaulting to lowercase
    df_src.columns = [c.upper() for c in df_src.columns]
    df_tgt.columns = [c.upper() for c in df_tgt.columns]
    
    return df_src, df_tgt

# ---------------------------------------------------------
# 3. ETL TEST CASES
# ---------------------------------------------------------

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
    
    # Sort both DataFrames by Primary Key (MOVIEID) to ensure alignment
    df_src_sorted = df_src.sort_values("MOVIEID").reset_index(drop=True)
    df_tgt_sorted = df_tgt.sort_values("MOVIEID").reset_index(drop=True)
    
    # Pandas Testing utility provides a detailed breakdown if data differs
    pd.testing.assert_frame_equal(df_src_sorted, df_tgt_sorted)

def test_data_quality_nulls(get_data):
    """TEST: Ensure mandatory columns (Title) have no NULL values in Target"""
    _, df_tgt = get_data
    null_count = df_tgt['MOVIETITLE'].isnull().sum()
    
    assert null_count == 0, f"❌ Data Quality Issue: Found {null_count} NULLs in Target Table!"