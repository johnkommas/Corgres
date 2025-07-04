import os
import pandas as pd
import tempfile
from etl import read_excel, map_columns, transform_data, export_to_excel, process_excel_file

def create_test_excel():
    """Create a test Excel file with sample data"""
    # Sample data with columns that don't match the required format
    data = {
        'Item Code': ['P001', 'P002', 'P003'],
        'Item Name': ['Product 1', 'Product 2', 'Product 3'],
        'UOM': ['PCS', 'KG', 'BOX'],
        'VAT': ['24%', '13%', '24%'],
        'Item Barcode': ['1234567890123', '2345678901234', '3456789012345'],
        'Pallet Code': ['PLT001', 'PLT002', 'PLT003'],
        'Item Weight': [1.5, 2.3, 5.0],
        'Item Height': [10, 15, 20],
        'Item Width': [5, 8, 12],
        'Item Length': [20, 25, 30],
        'Warehouse Location': ['A1', 'B2', 'C3'],
        'Min Stock': [10, 15, 20],
        'Max Stock': [100, 150, 200],
        'Reorder Level': [20, 30, 40]
    }

    df = pd.DataFrame(data)

    # Create a temporary file
    fd, temp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)

    # Save the DataFrame to the Excel file
    df.to_excel(temp_path, index=False)

    return temp_path

def test_read_excel():
    """Test reading an Excel file"""
    # Create a test Excel file
    test_file = create_test_excel()

    try:
        # Read the Excel file
        df = read_excel(test_file)

        # Check if the DataFrame was created correctly
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3  # 3 rows
        assert len(df.columns) == 14  # 14 columns

        print("✅ read_excel test passed")
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

def test_map_columns():
    """Test mapping columns from source to target format"""
    # Create a test DataFrame
    data = {
        'Item Code': ['P001', 'P002', 'P003'],
        'Item Name': ['Product 1', 'Product 2', 'Product 3'],
        'UOM': ['PCS', 'KG', 'BOX'],
        'VAT': ['24%', '13%', '24%'],
        'Item Barcode': ['1234567890123', '2345678901234', '3456789012345'],
        'Pallet Code': ['PLT001', 'PLT002', 'PLT003']
    }
    df = pd.DataFrame(data)

    # Define column mapping
    column_mapping = {
        'Product Barcode': 'Item Barcode',
        'Pallete Barcode': 'Pallet Code',
        'Description': 'Item Name',
        'Main Unit Measurement': 'UOM',
        'Vat Category': 'VAT'
    }

    # Map columns
    new_df = map_columns(df, column_mapping)

    # Check if the columns were mapped correctly
    assert 'Product Barcode' in new_df.columns
    assert 'Pallete Barcode' in new_df.columns
    assert 'Description' in new_df.columns
    assert 'Main Unit Measurement' in new_df.columns
    assert 'Vat Category' in new_df.columns

    # Check if the data was preserved
    assert new_df['Product Barcode'].iloc[0] == '1234567890123'
    assert new_df['Description'].iloc[1] == 'Product 2'

    print("✅ map_columns test passed")

def test_transform_data():
    """Test transforming data"""
    # Create a test DataFrame
    data = {
        'Product Barcode': ['1234567890123', '2345678901234', '3456789012345'],
        'Pallete Barcode': ['PLT001', 'PLT002', 'PLT003'],
        'Description': ['Product 1', 'Product 2', 'Product 3'],
        'Main Unit Measurement': ['PCS', 'KG', 'BOX'],
        'Vat Category': ['24%', '13%', '24%'],
        'Weight': ['1.5', '2.3', '5.0'],
        'Height': ['10', '15', '20'],
        'Width': ['5', '8', '12'],
        'Length': ['20', '25', '30']
    }
    df = pd.DataFrame(data)

    # Transform data
    transformed_df = transform_data(df)

    # Check if numeric columns were converted
    assert pd.api.types.is_numeric_dtype(transformed_df['Weight'])
    assert pd.api.types.is_numeric_dtype(transformed_df['Height'])
    assert pd.api.types.is_numeric_dtype(transformed_df['Width'])
    assert pd.api.types.is_numeric_dtype(transformed_df['Length'])

    print("✅ transform_data test passed")

def test_export_to_excel():
    """Test exporting to Excel"""
    # Create a test DataFrame with barcodes that include leading zeros
    # to verify they're preserved when formatted as text
    data = {
        'Product Barcode': ['0123456789012', '2345678901234', '3456789012345'],
        'Pallete Barcode': ['0000PLT001', 'PLT002', 'PLT003'],
        'Description': ['Product 1', 'Product 2', 'Product 3'],
        'Main Unit Measurement': ['PCS', 'KG', 'BOX'],
        'Vat Category': ['24%', '13%', '24%']
    }
    df = pd.DataFrame(data)

    # Create a temporary file for the output
    fd, temp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)

    try:
        # Export to Excel
        result_path = export_to_excel(df, temp_path)

        # Check if the file was created
        assert os.path.exists(result_path)

        # Read the file back and check if the data is correct
        # Use dtype=str for barcode columns to ensure they're read as text
        df_read = pd.read_excel(
            result_path, 
            dtype={'Product Barcode': str, 'Pallete Barcode': str}
        )

        # Basic checks
        assert len(df_read) == 3
        assert 'Product Barcode' in df_read.columns
        assert df_read['Description'].iloc[0] == 'Product 1'

        # Check if leading zeros are preserved (confirming text formatting)
        assert df_read['Product Barcode'].iloc[0] == '0123456789012'
        assert df_read['Pallete Barcode'].iloc[0] == '0000PLT001'

        print("✅ export_to_excel test passed with barcode text formatting verified")
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_process_excel_file():
    """Test the complete ETL process"""
    # Create a test Excel file with data that includes barcodes with leading zeros
    # First, create a DataFrame with our test data
    data = {
        'Item Barcode': ['0123456789012', '2345678901234', '3456789012345'],
        'Pallet Code': ['0000PLT001', 'PLT002', 'PLT003'],
        'Item Name': ['Product 1', 'Product 2', 'Product 3'],
        'UOM': ['PCS', 'KG', 'BOX'],
        'VAT': ['24%', '13%', '24%'],
        'Item Weight': [1.5, 2.3, 5.0],
        'Item Height': [10, 15, 20],
        'Item Width': [5, 8, 12],
        'Item Length': [20, 25, 30],
        'Warehouse Location': ['A1', 'B2', 'C3'],
        'Min Stock': [10, 15, 20],
        'Max Stock': [100, 150, 200],
        'Reorder Level': [20, 30, 40]
    }
    df = pd.DataFrame(data)

    # Create a temporary file for the input
    fd, test_file = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)

    # Save the DataFrame to the Excel file
    df.to_excel(test_file, index=False)

    # Create a temporary file for the output
    fd, output_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)

    # Define column mapping
    column_mapping = {
        'Product Barcode': 'Item Barcode',
        'Pallete Barcode': 'Pallet Code',
        'Description': 'Item Name',
        'Main Unit Measurement': 'UOM',
        'Vat Category': 'VAT',
        'Weight': 'Item Weight',
        'Height': 'Item Height',
        'Width': 'Item Width',
        'Length': 'Item Length',
        'Storage Location': 'Warehouse Location',
        'Min Stock Level': 'Min Stock',
        'Max Stock Level': 'Max Stock',
        'Reorder Point': 'Reorder Level'
    }

    try:
        # Process the Excel file
        result_path = process_excel_file(test_file, output_path, column_mapping)

        # Check if the file was created
        assert os.path.exists(result_path)

        # Read the file back and check if the data is correct
        # Use dtype=str for barcode columns to ensure they're read as text
        df_read = pd.read_excel(
            result_path,
            dtype={'Product Barcode': str, 'Pallete Barcode': str}
        )

        # Check if all required columns are present
        assert 'Product Barcode' in df_read.columns
        assert 'Pallete Barcode' in df_read.columns
        assert 'Description' in df_read.columns
        assert 'Main Unit Measurement' in df_read.columns
        assert 'Vat Category' in df_read.columns

        # Check if the data was mapped correctly
        assert df_read['Description'].iloc[1] == 'Product 2'

        # Check if leading zeros are preserved (confirming text formatting)
        assert df_read['Product Barcode'].iloc[0] == '0123456789012'
        assert df_read['Pallete Barcode'].iloc[0] == '0000PLT001'

        print("✅ process_excel_file test passed with barcode text formatting verified")
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
        if os.path.exists(output_path):
            os.remove(output_path)

if __name__ == "__main__":
    print("Running ETL tests...")
    test_read_excel()
    test_map_columns()
    test_transform_data()
    test_export_to_excel()
    test_process_excel_file()
    print("All tests passed! ✅")
