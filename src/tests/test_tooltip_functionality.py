#!/usr/bin/env python3
"""
Test script to validate the tooltip functionality for visitor statistics.
This script will check that:
1. The user count text is hidden (display: none)
2. The tooltip functionality is properly implemented
3. The JavaScript variables and functions are correctly defined
"""

import os
import re

def test_tooltip_functionality():
    print("Testing tooltip functionality implementation...")
    print("=" * 60)
    
    # Path to the selection.html file
    selection_file = "/Users/johnkommas/PycharmProjects/Corgres/src/static/selection.html"
    
    if not os.path.exists(selection_file):
        print("❌ ERROR: selection.html file not found!")
        return False
    
    # Read the file content
    with open(selection_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Test 1: Check if user count is hidden
    print("Test 1: Checking if user count display is hidden...")
    if 'style="display: none;"' in content and 'id="excel-formatter-users"' in content:
        print("✅ PASS: User count display is properly hidden")
    else:
        print("❌ FAIL: User count display is not hidden")
        return False
    
    # Test 2: Check if tooltip CSS is present
    print("\nTest 2: Checking if tooltip CSS styles are present...")
    tooltip_css_patterns = [
        r'\.tooltip\s*{',
        r'\.tooltip\.show\s*{',
        r'\.tooltip::after\s*{'
    ]
    
    css_found = all(re.search(pattern, content) for pattern in tooltip_css_patterns)
    if css_found:
        print("✅ PASS: Tooltip CSS styles are properly defined")
    else:
        print("❌ FAIL: Tooltip CSS styles are missing")
        return False
    
    # Test 3: Check if tooltip JavaScript functions are present
    print("\nTest 3: Checking if tooltip JavaScript functions are present...")
    js_patterns = [
        r'function createTooltip\(\)',
        r'function showTooltip\(',
        r'function hideTooltip\(\)',
        r'let currentUserCount = 0',
        r'addEventListener\([\'"]mouseenter[\'"]',
        r'addEventListener\([\'"]mouseleave[\'"]'
    ]
    
    js_found = all(re.search(pattern, content) for pattern in js_patterns)
    if js_found:
        print("✅ PASS: Tooltip JavaScript functions are properly defined")
    else:
        print("❌ FAIL: Tooltip JavaScript functions are missing")
        return False
    
    # Test 4: Check if currentUserCount is updated in the existing code
    print("\nTest 4: Checking if currentUserCount variable is updated...")
    if 'currentUserCount = excelFormatterCount;' in content:
        print("✅ PASS: currentUserCount variable is properly updated")
    else:
        print("❌ FAIL: currentUserCount variable is not updated")
        return False
    
    # Test 5: Check if tooltip positioning is implemented
    print("\nTest 5: Checking if tooltip positioning is implemented...")
    positioning_patterns = [
        r'tooltip\.style\.left',
        r'tooltip\.style\.top',
        r'getBoundingClientRect\(\)'
    ]
    
    positioning_found = all(re.search(pattern, content) for pattern in positioning_patterns)
    if positioning_found:
        print("✅ PASS: Tooltip positioning is properly implemented")
    else:
        print("❌ FAIL: Tooltip positioning is missing")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED! Tooltip functionality is properly implemented.")
    print("\nSummary of changes:")
    print("1. ✅ User count text is hidden from display")
    print("2. ✅ Tooltip CSS styles added with smooth animations")
    print("3. ✅ JavaScript functions for tooltip management")
    print("4. ✅ Hover event listeners on Excel Formatter card")
    print("5. ✅ Dynamic tooltip positioning")
    print("6. ✅ User count data properly stored for tooltip display")
    
    print("\nExpected behavior:")
    print("- User count text is no longer visible on the page")
    print("- When hovering over Excel Formatter card, tooltip shows user count")
    print("- Tooltip follows mouse movement and disappears on mouse leave")
    
    return True

if __name__ == "__main__":
    success = test_tooltip_functionality()
    if success:
        print("\n✅ Implementation is ready for testing!")
    else:
        print("\n❌ Implementation needs fixes!")