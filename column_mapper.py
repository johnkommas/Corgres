import os
import json
from typing import Dict, Set, List, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)

# File to store column mappings
MAPPINGS_FILE = "column_mappings.json"

def load_mappings() -> Dict[str, Set[str]]:
    """
    Load column mappings from the JSON file.
    
    Returns:
        Dictionary with required column names as keys and sets of possible source column names as values
    """
    try:
        if os.path.exists(MAPPINGS_FILE):
            with open(MAPPINGS_FILE, 'r') as f:
                # JSON can't store sets, so we convert lists back to sets
                mappings_dict = json.load(f)
                return {k: set(v) for k, v in mappings_dict.items()}
        else:
            logger.info(f"Mappings file {MAPPINGS_FILE} not found. Creating new mappings.")
            return {}
    except Exception as e:
        logger.error(f"Error loading column mappings: {str(e)}")
        return {}

def save_mappings(mappings: Dict[str, Set[str]]) -> bool:
    """
    Save column mappings to the JSON file.
    
    Args:
        mappings: Dictionary with required column names as keys and sets of possible source column names as values
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert sets to lists for JSON serialization
        serializable_mappings = {k: list(v) for k, v in mappings.items()}
        with open(MAPPINGS_FILE, 'w') as f:
            json.dump(serializable_mappings, f, indent=2)
        logger.info(f"Column mappings saved to {MAPPINGS_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error saving column mappings: {str(e)}")
        return False

def add_mapping(column_mapping: Dict[str, str]) -> bool:
    """
    Add a new column mapping to the stored mappings.
    
    Args:
        column_mapping: Dictionary mapping required column names to source column names
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load existing mappings
        mappings = load_mappings()
        
        # Add new mappings
        for target_col, source_col in column_mapping.items():
            if source_col:  # Only add non-empty mappings
                if target_col not in mappings:
                    mappings[target_col] = set()
                mappings[target_col].add(source_col)
        
        # Save updated mappings
        return save_mappings(mappings)
    except Exception as e:
        logger.error(f"Error adding column mapping: {str(e)}")
        return False

def get_suggestions(column_names: List[str]) -> Dict[str, str]:
    """
    Get suggestions for column mapping based on stored mappings.
    
    Args:
        column_names: List of column names from the source file
        
    Returns:
        Dictionary with suggested mappings (required column names as keys, suggested source column names as values)
    """
    try:
        # Load existing mappings
        mappings = load_mappings()
        
        # Create a dictionary to store suggestions
        suggestions = {}
        
        # For each required column, check if any of the source columns match stored mappings
        for target_col, possible_sources in mappings.items():
            for source_col in column_names:
                if source_col in possible_sources:
                    suggestions[target_col] = source_col
                    break
        
        logger.info(f"Generated {len(suggestions)} column mapping suggestions")
        return suggestions
    except Exception as e:
        logger.error(f"Error getting column mapping suggestions: {str(e)}")
        return {}