
import os

file_path = r"C:\DEV OPS\PROJECT LUCAS\templates\dashboards\system_settings.html"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the target string with the newline and indentation
target_string = """        academicYearDates[{{ year.id }
    }] = {"""

replacement_string = """        academicYearDates[{{ year.id }}] = {"""

if target_string in content:
    new_content = content.replace(target_string, replacement_string)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully replaced the split Jinja tag.")
else:
    print("Target string not found. Checking for variations...")
    # Debugging: print around line 3533
    lines = content.splitlines()
    if len(lines) > 3530:
        print("Lines around 3533:")
        for i in range(3530, 3540):
            if i < len(lines):
                print(f"{i+1}: {repr(lines[i])}")
