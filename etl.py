import pandas as pd
import os
import json
from typing import List, Dict, Any, Optional, Tuple
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define the required columns for the Softone ERP system
REQUIRED_COLUMNS = [
    'Product Barcode',
    'Pallete Barcode',
    'Description',
    'Main Unit Measurement',
    'Vat Category',
    # Logistics information
    'Weight',
    'Height',
    'Width',
    'Length',
    'Storage Location',
    'Min Stock Level',
    'Max Stock Level',
    'Reorder Point'
]

def read_excel(file_path: str) -> pd.DataFrame:
    """
    Read an Excel file into a pandas DataFrame

    Args:
        file_path: Path to the Excel file

    Returns:
        DataFrame containing the Excel data
    """
    try:
        logger.info(f"Reading Excel file: {file_path}")
        df = pd.read_excel(file_path)
        logger.info(f"Successfully read Excel file with {len(df)} rows and {len(df.columns)} columns")
        return df
    except Exception as e:
        logger.error(f"Error reading Excel file: {str(e)}")
        raise

def map_columns(df: pd.DataFrame, column_mapping: Dict[str, str]) -> pd.DataFrame:
    """
    Map columns from the source DataFrame to the required format

    Args:
        df: Source DataFrame
        column_mapping: Dictionary mapping source column names to required column names

    Returns:
        DataFrame with mapped columns
    """
    try:
        logger.info("Mapping columns according to provided mapping")
        # Create a new DataFrame with the required columns
        new_df = pd.DataFrame()

        # Map columns according to the provided mapping
        for target_col, source_col in column_mapping.items():
            if source_col in df.columns:
                new_df[target_col] = df[source_col]
            else:
                logger.warning(f"Source column '{source_col}' not found in the input file. Creating empty column for '{target_col}'")
                new_df[target_col] = None

        # Add any missing required columns
        for col in REQUIRED_COLUMNS:
            if col not in new_df.columns:
                logger.warning(f"Required column '{col}' not mapped. Creating empty column.")
                new_df[col] = None

        # Reorder columns to match the required order
        ordered_cols = [col for col in REQUIRED_COLUMNS if col in new_df.columns]
        other_cols = [col for col in new_df.columns if col not in REQUIRED_COLUMNS]
        new_df = new_df[ordered_cols + other_cols]

        logger.info(f"Successfully mapped columns. New DataFrame has {len(new_df.columns)} columns")
        return new_df
    except Exception as e:
        logger.error(f"Error mapping columns: {str(e)}")
        raise

def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply any necessary transformations to the data

    Args:
        df: Source DataFrame

    Returns:
        Transformed DataFrame
    """
    try:
        logger.info("Applying data transformations")
        # Here you can add any specific transformations needed
        # For example, data type conversions, calculations, etc.

        # Example: Convert numeric columns to appropriate types
        numeric_cols = ['Weight', 'Height', 'Width', 'Length', 'Min Stock Level', 'Max Stock Level', 'Reorder Point']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        logger.info("Data transformation completed")
        return df
    except Exception as e:
        logger.error(f"Error transforming data: {str(e)}")
        raise

def load_row_mappings() -> Dict[str, Dict[str, str]]:
    """
    Load row mappings from rown_mapping.json file

    Returns:
        Dictionary with column names as keys and dictionaries of value mappings as values
    """
    try:
        logger.info("Loading row mappings from rown_mapping.json")
        if os.path.exists("rown_mapping.json"):
            with open("rown_mapping.json", "r") as f:
                mappings = json.load(f)
            logger.info(f"Loaded row mappings for {len(mappings)} columns")
            return mappings
        else:
            logger.warning("rown_mapping.json file not found")
            return {}
    except Exception as e:
        logger.error(f"Error loading row mappings: {str(e)}")
        return {}

def add_row_mapping(column: str, value: str, mapped_value: str) -> bool:
    """
    Add a row mapping to rown_mapping.json

    Args:
        column: Column name
        value: Original value
        mapped_value: Mapped value

    Returns:
        True if mapping was added successfully, False otherwise
    """
    try:
        logger.info(f"Adding row mapping for column '{column}': {value} -> {mapped_value}")

        # Load existing mappings
        mappings = load_row_mappings()

        # Add new mapping
        if column not in mappings:
            mappings[column] = {}

        mappings[column][value] = mapped_value

        # Save mappings
        with open("rown_mapping.json", "w") as f:
            json.dump(mappings, f, indent=2)

        logger.info(f"Row mapping added successfully")
        return True
    except Exception as e:
        logger.error(f"Error adding row mapping: {str(e)}")
        return False

def validate_column_values(df: pd.DataFrame, column: str, acceptable_values: List[str] = None) -> Dict[str, Any]:
    """
    Validate column values against acceptable values

    Args:
        df: Source DataFrame
        column: Column name to validate
        acceptable_values: List of acceptable values (optional)

    Returns:
        Dictionary with validation results
    """
    try:
        logger.info(f"Validating {column} values")

        # Check if column exists
        if column not in df.columns:
            logger.warning(f"{column} column not found in DataFrame")
            return {
                "valid": True,
                "message": f"{column} column not found"
            }

        # If acceptable_values is not provided, try to get them from .env file
        if acceptable_values is None:
            # For Main Unit Measurement, get values from .env file
            if column == 'Main Unit Measurement':
                acceptable_values_str = os.getenv("MAIN_UNIT_MEASUREMENT_DEFAULT_VALUES", "")
                if not acceptable_values_str:
                    logger.warning("MAIN_UNIT_MEASUREMENT_DEFAULT_VALUES not found in .env file")
                    return {
                        "valid": True,
                        "message": "No acceptable values defined"
                    }
                acceptable_values = [val.strip() for val in acceptable_values_str.split(",")]
            else:
                logger.warning(f"No acceptable values provided for {column}")
                return {
                    "valid": True,
                    "message": "No acceptable values defined"
                }

        logger.info(f"Acceptable values for {column}: {acceptable_values}")

        # Get unique values from the column
        unique_values = df[column].dropna().unique().tolist()
        logger.info(f"Unique values found in {column}: {unique_values}")

        # Check if all unique values are acceptable
        invalid_values = [val for val in unique_values if val not in acceptable_values]

        if invalid_values:
            logger.warning(f"Invalid {column} values found: {invalid_values}")
            return {
                "valid": False,
                "message": f"Invalid {column} values found",
                "invalid_values": invalid_values,
                "acceptable_values": acceptable_values,
                "column": column
            }
        else:
            logger.info(f"All {column} values are valid")
            return {
                "valid": True,
                "message": f"All {column} values are valid"
            }
    except Exception as e:
        logger.error(f"Error validating {column} values: {str(e)}")
        return {
            "valid": False,
            "message": f"Error validating: {str(e)}"
        }

def validate_main_unit_measurement(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate Main Unit Measurement values against acceptable values from .env file

    Args:
        df: Source DataFrame

    Returns:
        Dictionary with validation results
    """
    return validate_column_values(df, 'Main Unit Measurement')

def export_to_excel(df: pd.DataFrame, output_path: str) -> str:
    """
    Export DataFrame to Excel file

    Args:
        df: DataFrame to export
        output_path: Path where the Excel file will be saved

    Returns:
        Path to the saved Excel file
    """
    try:
        logger.info(f"Exporting data to Excel file: {output_path}")
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Create a writer with the specified output path
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Convert barcode columns to string to ensure they're treated as text
            if 'Product Barcode' in df.columns:
                df['Product Barcode'] = df['Product Barcode'].astype(str)

            if 'Pallete Barcode' in df.columns:
                df['Pallete Barcode'] = df['Pallete Barcode'].astype(str)

            # Export to Excel
            df.to_excel(writer, index=False)

            # Get the worksheet
            worksheet = writer.sheets['Sheet1']

            # Format barcode columns as text
            for col_idx, col_name in enumerate(df.columns):
                if col_name in ['Product Barcode', 'Pallete Barcode']:
                    # Excel column letters start from A
                    col_letter = chr(65 + col_idx)
                    # Format all cells in the column as text (skip header row)
                    for row_idx in range(2, len(df) + 2):  # +2 because Excel is 1-indexed and we have a header row
                        cell = f"{col_letter}{row_idx}"
                        worksheet[cell].number_format = '@'

        logger.info(f"Successfully exported {len(df)} rows to Excel file with barcode columns formatted as text")
        return output_path
    except Exception as e:
        logger.error(f"Error exporting to Excel: {str(e)}")
        raise

def process_excel_file(input_path: str, output_path: str, column_mapping: Dict[str, str]) -> str:
    """
    Process an Excel file: read, transform, and export

    Args:
        input_path: Path to the input Excel file
        output_path: Path where the output Excel file will be saved
        column_mapping: Dictionary mapping source column names to required column names

    Returns:
        Path to the saved Excel file
    """
    try:
        logger.info(f"Processing Excel file: {input_path}")

        # Read the Excel file
        df = read_excel(input_path)

        # Map columns
        df = map_columns(df, column_mapping)

        # Transform data
        df = transform_data(df)

        # Export to Excel
        result_path = export_to_excel(df, output_path)

        logger.info(f"Excel processing completed. Output file: {result_path}")
        return result_path
    except Exception as e:
        logger.error(f"Error processing Excel file: {str(e)}")
        raise

def get_column_mapping_template() -> Dict[str, str]:
    """
    Get a template for column mapping

    Returns:
        Dictionary with required columns as keys and empty strings as values
    """
    return {col: "" for col in REQUIRED_COLUMNS}

def get_unique_column_values(df: pd.DataFrame, max_values: int = 3) -> Dict[str, List[str]]:
    """
    Get unique values for each column in the DataFrame

    Args:
        df: Source DataFrame
        max_values: Maximum number of unique values to return for each column

    Returns:
        Dictionary with column names as keys and lists of unique values as values
    """
    try:
        logger.info(f"Extracting unique values for each column (max {max_values} per column)")
        unique_values = {}

        for col in df.columns:
            # Get unique values for the column, excluding NaN values
            col_values = df[col].dropna().unique()

            # Convert all values to strings and limit to max_values
            col_values = [str(val) for val in col_values[:max_values]]

            unique_values[col] = col_values

        logger.info(f"Successfully extracted unique values for {len(unique_values)} columns")
        return unique_values
    except Exception as e:
        logger.error(f"Error extracting unique values: {str(e)}")
        return {}
