
import os
import re

print("Starting fix script...")

file_path = "C:\\DEV OPS\\PROJECT LUCAS\\templates\\dashboards\\system_settings.html"

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    print(f"Read file. Size: {len(content)} bytes.")

    # Regex to find the broken pattern, handling variable whitespace
    pattern = re.compile(r'academicYearDates\[\{\{\s*year\.id\s*\n\s*\}\}\]\s*=\s*\{')
    
    # Simple search for the split lines
    # Look for: academicYearDates[{{ year.id }
    #           }] = {
    
    # We will iterate lines to find it to be sure
    lines = content.splitlines()
    found_line_idx = -1
    
    for i, line in enumerate(lines):
        if "academicYearDates[{{ year.id" in line and not "}}]" in line:
            print(f"Found potential match at line {i+1}: {repr(line)}")
            # Check next line
            if i + 1 < len(lines):
                next_line = lines[i+1]
                print(f"Next line {i+2}: {repr(next_line)}")
                if "}] = {" in next_line:
                    found_line_idx = i
                    break
    
    if found_line_idx != -1:
        print(f"Identified split tag at line {found_line_idx+1}. Merging...")
        
        # Merge the lines
        lines[found_line_idx] = lines[found_line_idx].rstrip() + "}] = {"
        # Remove the next line (which contained only "}] = {")
        del lines[found_line_idx + 1]
        
        # Reconstruct content
        new_content = "\n".join(lines)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully merged lines and saved file.")
        
    else:
        print("Could not find the split tag pattern by line iteration.")
        # Print lines 3530-3540 for manual inspection
        start = max(0, 3530)
        end = min(len(lines), 3540)
        for i in range(start, end):
            print(f"{i+1}: {repr(lines[i])}")

except Exception as e:
    print(f"An error occurred: {e}")
