import pandas as pd
import os
from typing import List, Dict, Any, Optional, Tuple
import logging

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
        
        # Export to Excel
        df.to_excel(output_path, index=False)
        
        logger.info(f"Successfully exported {len(df)} rows to Excel file")
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