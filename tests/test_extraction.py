import pandas as pd
from pandas.testing import assert_frame_equal
from custom_modules.extraction import process_csv



def test_process_csv():
    # assemble
    csv_file = "tests/example1.csv"
    csv_file_expected = "tests/expected.csv"

    expected_df = pd.read_csv(csv_file_expected)
    expected_df = expected_df.astype(str)
    
    # act
    result_df = process_csv(csv_file)
    result_df = result_df.astype(str)

    # assert
    assert_frame_equal(expected_df, result_df.reset_index(drop=True), check_dtype=False)