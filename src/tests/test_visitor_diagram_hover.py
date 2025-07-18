#!/usr/bin/env python3
"""
Test script to validate the visitor diagram hover functionality.
This script will check that:
1. The node labels are hidden (display: none)
2. The hover effects show count inside icons with grey color and bigger size
3. The JavaScript no longer creates node-label elements
"""

import os
import re

def test_visitor_diagram_hover():
    print("Testing visitor diagram hover functionality implementation...")
    print("=" * 70)
    
    # Path to the selection.html file
    selection_file = "/Users/johnkommas/PycharmProjects/Corgres/src/static/selection.html"
    
    if not os.path.exists(selection_file):
        print("❌ ERROR: selection.html file not found!")
        return False
    
    # Read the file content
    with open(selection_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Test 1: Check if node labels are hidden
    print("Test 1: Checking if node labels are hidden...")
    if '.tree li .node-label' in content and 'display: none;' in content:
        print("✅ PASS: Node labels are properly hidden")
    else:
        print("❌ FAIL: Node labels are not hidden")
        return False
    
    # Test 2: Check if count display CSS is present
    print("\nTest 2: Checking if count display CSS is present...")
    count_css_patterns = [
        r'\.tree li \.node::after\s*{',
        r'content: attr\(data-count\)',
        r'opacity: 0',
        r'\.tree li \.node:hover::after\s*{',
        r'opacity: 1'
    ]
    
    css_found = all(re.search(pattern, content) for pattern in count_css_patterns)
    if css_found:
        print("✅ PASS: Count display CSS is properly defined")
    else:
        print("❌ FAIL: Count display CSS is missing")
        return False
    
    # Test 3: Check if hover effects are updated
    print("\nTest 3: Checking if hover effects are updated...")
    hover_patterns = [
        r'background: #8e8e93.*Grey color on hover',
        r'transform: scale\(1\.2\).*Bigger size on hover',
        r'\.tree li \.node:hover i.*opacity: 0.*Hide the icon on hover'
    ]
    
    hover_found = all(re.search(pattern, content, re.DOTALL) for pattern in hover_patterns)
    if hover_found:
        print("✅ PASS: Hover effects are properly updated")
    else:
        print("❌ FAIL: Hover effects are not properly updated")
        return False
    
    # Test 4: Check if all level-specific hover states use grey color
    print("\nTest 4: Checking if all level hover states use grey color...")
    grey_hover_count = len(re.findall(r'background: #8e8e93.*Grey color on hover', content))
    if grey_hover_count >= 4:  # Should be at least 4 levels
        print("✅ PASS: All level hover states use grey color")
    else:
        print("❌ FAIL: Not all level hover states use grey color")
        return False
    
    # Test 5: Check if node label creation is removed from JavaScript
    print("\nTest 5: Checking if node label creation is removed...")
    removed_patterns = [
        r'Root node label removed - count now shown on hover inside icon',
        r'Platform node label removed - count now shown on hover inside icon',
        r'Browser node label removed - count now shown on hover inside icon'
    ]
    
    removal_found = all(re.search(pattern, content) for pattern in removed_patterns)
    if removal_found:
        print("✅ PASS: Node label creation is properly removed")
    else:
        print("❌ FAIL: Node label creation is not properly removed")
        return False
    
    # Test 6: Check if old label creation code is gone
    print("\nTest 6: Checking if old label creation code is removed...")
    old_patterns = [
        r'const.*Label = document\.createElement\([\'"]div[\'"]\)',
        r'\.className = [\'"]node-label[\'"]',
        r'\.textContent = `\$\{.*\} Users`'
    ]
    
    old_code_found = any(re.search(pattern, content) for pattern in old_patterns)
    if not old_code_found:
        print("✅ PASS: Old label creation code is removed")
    else:
        print("❌ FAIL: Old label creation code still exists")
        return False
    
    print("\n" + "=" * 70)
    print("🎉 ALL TESTS PASSED! Visitor diagram hover functionality is properly implemented.")
    print("\nSummary of changes:")
    print("1. ✅ Node labels are hidden from display")
    print("2. ✅ CSS added to show count inside icons on hover")
    print("3. ✅ Hover effects make icons bigger (scale 1.2) and grey")
    print("4. ✅ Original icons are hidden on hover, count is shown instead")
    print("5. ✅ All tree levels use consistent grey hover color")
    print("6. ✅ JavaScript no longer creates node-label elements")
    
    print("\nExpected behavior:")
    print("- User count text is no longer visible above/below icons")
    print("- When hovering over any icon in the visitor diagram:")
    print("  • Icon becomes bigger (20% larger)")
    print("  • Icon turns grey (#8e8e93)")
    print("  • Original icon disappears")
    print("  • User count number appears inside the icon")
    print("- When mouse leaves, icon returns to normal state")
    
    return True

if __name__ == "__main__":
    success = test_visitor_diagram_hover()
    if success:
        print("\n✅ Implementation is ready for testing!")
    else:
        print("\n❌ Implementation needs fixes!")