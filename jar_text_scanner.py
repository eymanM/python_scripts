#!/usr/bin/env python3
"""
JAR Text Scanner

This script searches for text within JAR files and displays the matches.
It can recursively search through directories and find any text in various 
file types within JAR archives.

Usage examples:
    # Search for "import" in all JAR files in the current directory
    python jar_text_scanner.py "import"
    
    # Search in a specific directory
    python jar_text_scanner.py "import" -d /path/to/directory
    
    # Show more matches per JAR file
    python jar_text_scanner.py "import" -l 20
    
    # Increase the total match limit
    python jar_text_scanner.py "import" --total-limit 2000
    
    # Perform binary search on all files
    python jar_text_scanner.py "import" -b
    
    # Search in a specific JAR file
    python jar_text_scanner.py "import" -j upo-5.29.002.jar
    
    # Deep inspection mode for class files
    python jar_text_scanner.py "import" -j upo-5.29.002.jar -b --deep
"""
import os
import zipfile
import asyncio
import re
import argparse
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


async def scan_jar_file_for_text(jar_path, search_text, case_sensitive=False, binary_mode=False, deep_inspection=False):
    """
    Scans a JAR file for the specified text in all text-based files.
    Returns a list of tuples (file_name, jar_path, line_number, matching_line).
    """
    results = []
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            # Get list of all files in the JAR
            file_list = jar.namelist()
            
            # Common text file extensions to check
            text_extensions = [
                '.java', '.class', '.xml', '.properties', '.txt', '.md', 
                '.yml', '.yaml', '.json', '.html', '.css', '.js', '.jsp',
                '.config', '.ini', '.conf', '.MF', '.sql'
            ]
            
            # Prepare search text for binary mode if needed
            search_bytes = search_text.encode('utf-8') if binary_mode else None
            
            # Check each file that may contain text
            for file_name in file_list:
                # In binary mode, check all files, otherwise filter by extension
                is_target_file = True if binary_mode else (any(file_name.endswith(ext) for ext in text_extensions) or '.' not in file_name)
                
                if is_target_file:
                    try:
                        with jar.open(file_name) as jar_file:
                            if binary_mode:
                                # Binary search mode
                                content = jar_file.read()
                                
                                if search_bytes in content:
                                    # For binary matches, try to show context
                                    match_pos = content.find(search_bytes)
                                    start_pos = max(0, match_pos - 20)
                                    end_pos = min(len(content), match_pos + len(search_bytes) + 20)
                                    
                                    context = content[start_pos:end_pos]
                                    context_str = str(context)
                                    
                                    if file_name.endswith('.class') and deep_inspection:
                                        # For class files, extract string literals
                                        string_matches = re.findall(b'[\x01-\x7F]{3,}', content)
                                        if string_matches:
                                            context_str = "String literals: " + " | ".join([str(s) for s in string_matches[:20]])
                                    
                                    results.append((file_name, str(jar_path), 0, f"Binary match at position {match_pos}: {context_str}"))
                            else:
                                # Text search mode
                                content = jar_file.read().decode('utf-8', errors='ignore')
                                
                                # Search for the text in each line
                                lines = content.splitlines()
                                for line_num, line in enumerate(lines, 1):
                                    if case_sensitive:
                                        if search_text in line:  
                                            results.append((file_name, str(jar_path), line_num, line.strip()))
                                    else:
                                        if search_text.lower() in line.lower():  
                                            results.append((file_name, str(jar_path), line_num, line.strip()))
                    except Exception as e:
                        # Skip files that can't be read
                        pass
    except (zipfile.BadZipFile, Exception) as e:
        print(f"Error processing {jar_path}: {e}")
    
    return results


async def find_jar_files(directory):
    """
    Recursively finds all .jar files in the given directory.
    Returns a list of paths to JAR files.
    """
    jar_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.jar'):
                jar_files.append(Path(os.path.join(root, file)))
    
    return jar_files


async def process_jar_files(directory, search_text, case_sensitive=False, binary_mode=False, deep_inspection=False):
    """
    Process all JAR files found in directory recursively, searching for the specified text.
    Returns a dictionary mapping JAR file paths to lists of found matches.
    """
    # Find all JAR files
    jar_files = await find_jar_files(directory)
    print(f"Found {len(jar_files)} JAR files to process.")
    
    # Process JAR files in parallel using a thread pool
    jar_to_matches = {}
    with ThreadPoolExecutor() as executor:
        # Create a list of tasks for scanning JAR files
        tasks = [scan_jar_file_for_text(jar_path, search_text, case_sensitive, binary_mode, deep_inspection) for jar_path in jar_files]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        # Aggregate results
        for i, jar_results in enumerate(results):
            if jar_results:
                jar_path = str(jar_files[i])
                jar_to_matches[jar_path] = jar_results
    
    return jar_to_matches


async def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Search for text in JAR files')
    parser.add_argument('search_text', help='Text to search for in JAR files')
    parser.add_argument('-d', '--directory', default=os.getcwd(),
                      help='Directory to search (default: current directory)')
    parser.add_argument('-l', '--limit', type=int, default=10,
                      help='Maximum number of matches to display per JAR file (default: 10)')
    parser.add_argument('--total-limit', type=int, default=1000,
                      help='Total maximum number of matches to display (default: 1000)')
    parser.add_argument('-c', '--case-sensitive', action='store_true',
                      help='Perform case-sensitive search (default: case-insensitive)')
    parser.add_argument('-b', '--binary', action='store_true',
                      help='Perform binary search on all files (useful for finding text in compiled code)')
    parser.add_argument('-j', '--jar', 
                      help='Search in a specific JAR file instead of searching all JAR files')
    parser.add_argument('--deep', action='store_true',
                      help='Deep inspection mode for class files (extracts string literals)')
    args = parser.parse_args()
    
    # Get search text and directory from arguments
    search_text = args.search_text
    current_dir = args.directory
    limit_per_jar = args.limit
    total_limit = args.total_limit
    case_sensitive = args.case_sensitive
    binary_mode = args.binary
    specific_jar = args.jar
    deep_inspection = args.deep
    
    # Configure stdout to handle encoding issues
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    
    # If a specific JAR is specified, only scan that JAR
    if specific_jar:
        jar_path = os.path.join(current_dir, specific_jar) if not os.path.isabs(specific_jar) else specific_jar
        if not os.path.exists(jar_path):
            print(f"Error: JAR file '{jar_path}' not found.")
            return
        print(f"Scanning for '{search_text}' in JAR file: {jar_path}")
        
        # Scan the specific JAR file
        results = await scan_jar_file_for_text(jar_path, search_text, case_sensitive, binary_mode, deep_inspection)
        jar_to_matches = {jar_path: results} if results else {}
    else:
        print(f"Scanning for '{search_text}' in JAR files within: {current_dir}")
        # Process all JAR files
        jar_to_matches = await process_jar_files(current_dir, search_text, case_sensitive, binary_mode, deep_inspection)
    
    # Print results
    print("\nSearch results:")
    print("-" * 80)
    
    if not jar_to_matches:
        print(f"No occurrences of '{search_text}' found in any JAR files.")
        
        # Special case for quoted strings, provide suggestion
        if '"' in search_text:
            print("\nNote: Your search string contains quotes which may need special handling.")
            print("Try searching for parts of the string or using the --deep flag for more thorough inspection.")
            print("For example: python jar_text_scanner.py \"Pattern\" -j upo-5.29.002.jar -b --deep")
    else:
        total_matches = 0
        displayed_matches = 0
        total_jar_count = len(jar_to_matches)
        
        for jar_path in sorted(jar_to_matches.keys()):
            matches = jar_to_matches[jar_path]
            total_matches += len(matches)
            
            print(f"JAR: {jar_path} ({len(matches)} matches)")
            
            # Limit the number of matches displayed per JAR file
            display_count = min(len(matches), limit_per_jar)
            for i, (file_name, _, line_num, line) in enumerate(matches[:display_count]):
                try:
                    print(f"  - {file_name}:{line_num}: {line}")
                except UnicodeEncodeError:
                    # Handle encoding errors by replacing problematic characters
                    safe_line = line.encode('ascii', 'replace').decode('ascii')
                    print(f"  - {file_name}:{line_num}: {safe_line}")
                    
            # Display message if not all matches are shown
            if len(matches) > limit_per_jar:
                print(f"  ... and {len(matches) - limit_per_jar} more matches (use --limit to show more)")
                
            print()
            
            # Track total displayed matches
            displayed_matches += display_count
            
            # Check if we've hit the total display limit
            if displayed_matches >= total_limit:
                remaining_jars = total_jar_count - (list(jar_to_matches.keys()).index(jar_path) + 1)
                if remaining_jars > 0:
                    print(f"Output limit reached. {remaining_jars} more JAR files with matches not shown.")
                    print(f"Use --total-limit to increase the maximum number of displayed matches.")
                break
    
        print(f"Summary: Found {total_matches} matches in {total_jar_count} JAR files.")
        if displayed_matches < total_matches:
            print(f"Displayed {displayed_matches} out of {total_matches} total matches.")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
