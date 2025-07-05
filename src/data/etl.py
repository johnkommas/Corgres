import pandas as pd
import os
import json
import re
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
    'Supplier Code',
    'Product Barcode',
    'Description',
    'Main Unit Measurement',
    'Alternative Unit Measurement',
    'Relation with MUM',
    'Box Barcode',
    'Box Height',
    'Box Width',
    'Box Length',
    'Palette Height',
    'Palette Width',
    'Palette Length',
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
        numeric_cols = ['Weight', 'Height', 'Width', 'Length', 'Min Stock Level', 'Max Stock Level', 'Reorder Point', 
                        'Palette Height', 'Palette Width', 'Palette Length']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Note: Default values for Palette Width and Length are now set in the export_to_excel function
        # to ensure they are applied just before the Excel file is created

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
        if os.path.exists("src/config/rown_mapping.json"):
            with open("src/config/rown_mapping.json", "r") as f:
                mappings = json.load(f)
            logger.info(f"Loaded row mappings for {len(mappings)} columns")
            return mappings
        else:
            logger.warning("src/config/rown_mapping.json file not found")
            return {}
    except Exception as e:
        logger.error(f"Error loading row mappings: {str(e)}")
        return {}

def update_column_mappings() -> bool:
    """
    Update the column mappings with all fields mentioned in the issue description.

    Returns:
        True if mappings were updated successfully, False otherwise
    """
    try:
        logger.info("Updating column mappings")

        # Define the column mappings
        column_mappings = {
            "Supplier Code": [
                "Supplier Code",
                "SUPPLIER_CODE"
            ],
            "Product Barcode": [
                "Barcode",
                "BARCODE",
                "Product Barcode"
            ],
            "Description": [
                "ΠΕΡΙΓΡΑΦΗ",
                "Description"
            ],
            "Main Unit Measurement": [
                "MM",
                "Main Unit Measurement",
                "MUM"
            ],
            "Alternative Unit Measurement": [
                "Alternative Unit Measurement",
                "AUM"
            ],
            "Relation with MUM": [
                "Relation with MUM",
                "MUM_RELATION"
            ],
            "Box Barcode": [
                "Box Barcode",
                "BOX_BARCODE"
            ],
            "Box Height": [
                "Box Height",
                "BOX_HEIGHT"
            ],
            "Box Width": [
                "Box Width",
                "BOX_WIDTH"
            ],
            "Box Length": [
                "Box Length",
                "BOX_LENGTH"
            ],
            "Palette Height": [
                "Palette Height",
                "PALETTE_HEIGHT"
            ],
            "Palette Width": [
                "Palette Width",
                "PALETTE_WIDTH"
            ],
            "Palette Length": [
                "Palette Length",
                "PALETTE_LENGTH"
            ],
            "Vat Category": [
                "VAT",
                "Vat Category"
            ]
        }

        # Save column mappings
        with open("src/config/column_mappings.json", "w") as f:
            json.dump(column_mappings, f, indent=2)

        logger.info("Column mappings updated successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating column mappings: {str(e)}")
        return False

def update_unit_measurement_mappings() -> bool:
    """
    Update the row mappings for Main Unit Measurement and Alternative Unit Measurement
    with the standard codes and values.

    Returns:
        True if mappings were updated successfully, False otherwise
    """
    try:
        logger.info("Updating unit measurement mappings")

        # Define the standard mappings for unit measurements
        unit_measurement_mappings = {
            "100": "100 ΖΕΥΓ",
            "101": "101 ΤΕΜ",
            "102": "102 ΚΙΛ",
            "103": "103 ΤΟΝ",
            "104": "104 ΜΕΤ",
            "105": "105 m2",
            "106": "106 ΔΟΧ",
            "107": "107 ΧΚΙΒ",
            "109": "109 ΚΟΥ",
            "110": "110 ΣΑΚ",
            "112": "112 ΛΙΤ",
            "113": "113 ΜΜΗΚ",
            "114": "114 ΚΑΝ",
            "116": "116 ΚΙΒ",
            "120": "120 ΣΕΤ"
        }

        # Also add mappings for the unit names themselves
        unit_name_mappings = {
            "ΖΕΥΓ": "100 ΖΕΥΓ",
            "ΤΕΜ": "101 ΤΕΜ",
            "ΚΙΛ": "102 ΚΙΛ",
            "ΤΟΝ": "103 ΤΟΝ",
            "ΜΕΤ": "104 ΜΕΤ",
            "m2": "105 m2",
            "ΔΟΧ": "106 ΔΟΧ",
            "ΧΚΙΒ": "107 ΧΚΙΒ",
            "ΚΟΥ": "109 ΚΟΥ",
            "ΣΑΚ": "110 ΣΑΚ",
            "ΛΙΤ": "112 ΛΙΤ",
            "ΜΜΗΚ": "113 ΜΜΗΚ",
            "ΚΑΝ": "114 ΚΑΝ",
            "ΚΙΒ": "116 ΚΙΒ",
            "ΣΕΤ": "120 ΣΕΤ"
        }

        # Combine both mappings
        combined_mappings = {**unit_measurement_mappings, **unit_name_mappings}

        # Load existing mappings
        mappings = load_row_mappings()

        # Update mappings for Main Unit Measurement
        if "Main Unit Measurement" not in mappings:
            mappings["Main Unit Measurement"] = {}

        mappings["Main Unit Measurement"] = {**mappings["Main Unit Measurement"], **combined_mappings}

        # Update mappings for Alternative Unit Measurement
        if "Alternative Unit Measurement" not in mappings:
            mappings["Alternative Unit Measurement"] = {}

        mappings["Alternative Unit Measurement"] = {**mappings["Alternative Unit Measurement"], **combined_mappings}

        # Save updated mappings
        with open("src/config/rown_mapping.json", "w") as f:
            json.dump(mappings, f, indent=2)

        logger.info("Unit measurement mappings updated successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating unit measurement mappings: {str(e)}")
        return False

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
        with open("src/config/rown_mapping.json", "w") as f:
            json.dump(mappings, f, indent=2)

        logger.info(f"Row mapping added successfully")
        return True
    except Exception as e:
        logger.error(f"Error adding row mapping: {str(e)}")
        return False

def get_unit_measurement_description(value: str) -> str:
    """
    Get the full description for a unit measurement code or name

    Args:
        value: Unit measurement code or name

    Returns:
        Full description of the unit measurement
    """
    # Define mappings between codes/names and their full descriptions
    unit_measurement_mappings = {
        "100": "100 ΖΕΥΓ",
        "101": "101 ΤΕΜ",
        "102": "102 ΚΙΛ",
        "103": "103 ΤΟΝ",
        "104": "104 ΜΕΤ",
        "105": "105 m2",
        "106": "106 ΔΟΧ",
        "107": "107 ΧΚΙΒ",
        "109": "109 ΚΟΥ",
        "110": "110 ΣΑΚ",
        "112": "112 ΛΙΤ",
        "113": "113 ΜΜΗΚ",
        "114": "114 ΚΑΝ",
        "116": "116 ΚΙΒ",
        "120": "120 ΣΕΤ",
        "ΖΕΥΓ": "100 ΖΕΥΓ",
        "ΤΕΜ": "101 ΤΕΜ",
        "ΚΙΛ": "102 ΚΙΛ",
        "ΤΟΝ": "103 ΤΟΝ",
        "ΜΕΤ": "104 ΜΕΤ",
        "m2": "105 m2",
        "ΔΟΧ": "106 ΔΟΧ",
        "ΧΚΙΒ": "107 ΧΚΙΒ",
        "ΚΟΥ": "109 ΚΟΥ",
        "ΣΑΚ": "110 ΣΑΚ",
        "ΛΙΤ": "112 ΛΙΤ",
        "ΜΜΗΚ": "113 ΜΜΗΚ",
        "ΚΑΝ": "114 ΚΑΝ",
        "ΚΙΒ": "116 ΚΙΒ",
        "ΣΕΤ": "120 ΣΕΤ"
    }

    # If the value is already a full description, return it
    if value in unit_measurement_mappings.values():
        return value

    # Otherwise, return the mapped description or the original value if not found
    return unit_measurement_mappings.get(value, value)

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

            # For unit measurement columns, add descriptions to the validation result
            if column in ['Main Unit Measurement', 'Alternative Unit Measurement']:
                # Map invalid values to their full descriptions
                invalid_values_with_descriptions = []
                for val in invalid_values:
                    invalid_values_with_descriptions.append({
                        'value': val,
                        'description': get_unit_measurement_description(val)
                    })

                # Map acceptable values to their full descriptions
                acceptable_values_with_descriptions = []
                for val in acceptable_values:
                    acceptable_values_with_descriptions.append({
                        'value': val,
                        'description': get_unit_measurement_description(val)
                    })

                return {
                    "valid": False,
                    "message": f"Invalid {column} values found",
                    "invalid_values": invalid_values,
                    "invalid_values_with_descriptions": invalid_values_with_descriptions,
                    "acceptable_values": acceptable_values,
                    "acceptable_values_with_descriptions": acceptable_values_with_descriptions,
                    "column": column
                }
            else:
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
    Validate Main Unit Measurement values against acceptable values

    Args:
        df: Source DataFrame

    Returns:
        Dictionary with validation results
    """
    # Define acceptable values for Main Unit Measurement - include all formats
    acceptable_values = ["100", "101", "102", "103", "104", "105", "106", "107", "109", 
                         "110", "112", "113", "114", "116", "120",
                         "ΖΕΥΓ", "ΤΕΜ", "ΚΙΛ", "ΤΟΝ", "ΜΕΤ", "m2", "ΔΟΧ", "ΧΚΙΒ", "ΚΟΥ", 
                         "ΣΑΚ", "ΛΙΤ", "ΜΜΗΚ", "ΚΑΝ", "ΚΙΒ", "ΣΕΤ",
                         "100 ΖΕΥΓ", "101 ΤΕΜ", "102 ΚΙΛ", "103 ΤΟΝ", "104 ΜΕΤ", "105 m2", 
                         "106 ΔΟΧ", "107 ΧΚΙΒ", "109 ΚΟΥ", "110 ΣΑΚ", "112 ΛΙΤ", 
                         "113 ΜΜΗΚ", "114 ΚΑΝ", "116 ΚΙΒ", "120 ΣΕΤ"]

    return validate_column_values(df, 'Main Unit Measurement', acceptable_values)

def validate_alternative_unit_measurement(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate Alternative Unit Measurement values against acceptable values

    Args:
        df: Source DataFrame

    Returns:
        Dictionary with validation results
    """
    # Define acceptable values for Alternative Unit Measurement - only include combined format
    acceptable_values = ["100 ΖΕΥΓ", "101 ΤΕΜ", "102 ΚΙΛ", "103 ΤΟΝ", "104 ΜΕΤ", "105 m2", 
                         "106 ΔΟΧ", "107 ΧΚΙΒ", "109 ΚΟΥ", "110 ΣΑΚ", "112 ΛΙΤ", 
                         "113 ΜΜΗΚ", "114 ΚΑΝ", "116 ΚΙΒ", "120 ΣΕΤ"]

    return validate_column_values(df, 'Alternative Unit Measurement', acceptable_values)

def extract_numeric_part(value):
    """
    Extract the numeric part from a unit measurement value

    Args:
        value: Unit measurement value (e.g., "102 ΚΙΛ")

    Returns:
        Numeric part of the value (e.g., "102")
    """
    if value is None:
        return value

    # Convert to string
    value_str = str(value)

    # Check if the value starts with a number
    match = re.match(r'^(\d+)', value_str)
    if match:
        return match.group(1)

    return value

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

        # Create a copy of the DataFrame to avoid modifying the original
        export_df = df.copy()

        # Set default values for Palette Width and Length if Palette Height has a value but they are empty
        # This ensures the default values are applied just before creating the Excel file
        if 'Palette Height' in export_df.columns and 'Palette Width' in export_df.columns and 'Palette Length' in export_df.columns:
            # Check if Palette Height has a value but Palette Width is empty
            mask_width = (~export_df['Palette Height'].isna()) & (export_df['Palette Width'].isna())
            if mask_width.any():
                logger.info(f"Setting default Palette Width (1.20) for {mask_width.sum()} rows before export")
                export_df.loc[mask_width, 'Palette Width'] = 1.20

            # Check if Palette Height has a value but Palette Length is empty
            mask_length = (~export_df['Palette Height'].isna()) & (export_df['Palette Length'].isna())
            if mask_length.any():
                logger.info(f"Setting default Palette Length (0.80) for {mask_length.sum()} rows before export")
                export_df.loc[mask_length, 'Palette Length'] = 0.80

        # Extract numeric part from unit measurement columns
        if 'Main Unit Measurement' in export_df.columns:
            logger.info("Extracting numeric part from Main Unit Measurement values")
            export_df['Main Unit Measurement'] = export_df['Main Unit Measurement'].apply(extract_numeric_part)

        if 'Alternative Unit Measurement' in export_df.columns:
            logger.info("Extracting numeric part from Alternative Unit Measurement values")
            export_df['Alternative Unit Measurement'] = export_df['Alternative Unit Measurement'].apply(extract_numeric_part)

        # Create a writer with the specified output path
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Convert barcode columns to string to ensure they're treated as text
            if 'Product Barcode' in export_df.columns:
                export_df['Product Barcode'] = export_df['Product Barcode'].astype(str)

            if 'Box Barcode' in export_df.columns:
                export_df['Box Barcode'] = export_df['Box Barcode'].astype(str)

            if 'Pallete Barcode' in export_df.columns:
                export_df['Pallete Barcode'] = export_df['Pallete Barcode'].astype(str)

            # Export to Excel
            export_df.to_excel(writer, index=False)

            # Get the worksheet
            worksheet = writer.sheets['Sheet1']

            # Format barcode columns as text
            for col_idx, col_name in enumerate(export_df.columns):
                if col_name in ['Product Barcode', 'Box Barcode', 'Pallete Barcode']:
                    # Excel column letters start from A
                    col_letter = chr(65 + col_idx)
                    # Format all cells in the column as text (skip header row)
                    for row_idx in range(2, len(export_df) + 2):  # +2 because Excel is 1-indexed and we have a header row
                        cell = f"{col_letter}{row_idx}"
                        worksheet[cell].number_format = '@'

        logger.info(f"Successfully exported {len(export_df)} rows to Excel file with barcode columns formatted as text")
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

        # Update column mappings
        update_column_mappings()

        # Update unit measurement mappings
        update_unit_measurement_mappings()

        # Read the Excel file
        df = read_excel(input_path)

        # Map columns
        df = map_columns(df, column_mapping)

        # Transform data
        df = transform_data(df)

        # Validate unit measurements
        main_unit_result = validate_main_unit_measurement(df)
        if not main_unit_result["valid"]:
            logger.warning(f"Main Unit Measurement validation: {main_unit_result['message']}")

        alt_unit_result = validate_alternative_unit_measurement(df)
        if not alt_unit_result["valid"]:
            logger.warning(f"Alternative Unit Measurement validation: {alt_unit_result['message']}")

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
