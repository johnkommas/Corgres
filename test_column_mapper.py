import os
import json
from column_mapper import add_mapping, load_mappings, MAPPINGS_FILE

# Clean up any existing mapping file
if os.path.exists(MAPPINGS_FILE):
    os.remove(MAPPINGS_FILE)
    print(f"Removed existing {MAPPINGS_FILE}")

# Test adding a mapping
test_mapping = {
    "Product Barcode": "Barcode",
    "Description": "Product Description"
}

print("Adding mapping for the first time...")
add_mapping(test_mapping)

# Load the mappings and print them
mappings = load_mappings()
print("Mappings after first add:")
for target_col, source_cols in mappings.items():
    print(f"  {target_col}: {source_cols}")

# Add the same mapping again
print("\nAdding the same mapping again...")
add_mapping(test_mapping)

# Load the mappings again and print them
mappings = load_mappings()
print("Mappings after second add:")
for target_col, source_cols in mappings.items():
    print(f"  {target_col}: {source_cols}")

# Verify that the number of source columns for each target column is still 1
# (i.e., no duplicates were added)
for target_col, source_cols in mappings.items():
    if len(source_cols) != 1:
        print(f"ERROR: Expected 1 source column for {target_col}, but got {len(source_cols)}")
    else:
        print(f"SUCCESS: {target_col} has 1 source column as expected")

# Clean up
if os.path.exists(MAPPINGS_FILE):
    os.remove(MAPPINGS_FILE)
    print(f"\nRemoved {MAPPINGS_FILE} after test")