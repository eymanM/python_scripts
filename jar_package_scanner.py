#!/usr/bin/env python3
import os
import zipfile
import asyncio
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


async def scan_jar_file(jar_path):
    """
    Scans a JAR file for Java package names.
    Returns a list of tuples (package_name, jar_path).
    """
    results = []
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            # Get list of all files in the JAR
            file_list = jar.namelist()
            
            # Look for .class files and extract package names
            for file_name in file_list:
                if file_name.endswith('.class'):
                    # Typical Java class path: com/example/mypackage/MyClass.class
                    # Convert to package name: com.example.mypackage
                    package_path = os.path.dirname(file_name)
                    if package_path:
                        package_name = package_path.replace('/', '.')
                        if package_name not in results:
                            results.append((package_name, str(jar_path)))
                
                # Also look for package declarations in Java source files if present
                elif file_name.endswith('.java'):
                    try:
                        with jar.open(file_name) as java_file:
                            content = java_file.read().decode('utf-8', errors='ignore')
                            # Look for package declaration using regex
                            matches = re.findall(r'package\s+([a-zA-Z0-9_.]+);', content)
                            for match in matches:
                                if match not in results:
                                    results.append((match, str(jar_path)))
                    except Exception:
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


async def process_jar_files(directory):
    """
    Process all JAR files found in directory recursively.
    Returns a dictionary mapping package names to JAR file paths.
    """
    # Find all JAR files
    jar_files = await find_jar_files(directory)
    print(f"Found {len(jar_files)} JAR files to process.")
    
    # Process JAR files in parallel using a thread pool
    package_to_jars = {}
    with ThreadPoolExecutor() as executor:
        # Create a list of tasks for scanning JAR files
        tasks = [scan_jar_file(jar_path) for jar_path in jar_files]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        # Aggregate results
        for jar_results in results:
            for package_name, jar_path in jar_results:
                if package_name in package_to_jars:
                    if jar_path not in package_to_jars[package_name]:
                        package_to_jars[package_name].append(jar_path)
                else:
                    package_to_jars[package_name] = [jar_path]
    
    return package_to_jars


async def main():
    # Get current directory
    current_dir = os.getcwd()
    print(f"Scanning for JAR files in: {current_dir}")
    
    # Process JAR files
    package_to_jars = await process_jar_files(current_dir)
    
    # Convert package_to_jars to jar_to_packages format
    jar_to_packages = {}
    for package_name, jar_paths in package_to_jars.items():
        for jar_path in jar_paths:
            if jar_path not in jar_to_packages:
                jar_to_packages[jar_path] = []
            jar_to_packages[jar_path].append(package_name)
    
    # Print results
    print("\nJAR files with package names:")
    print("-" * 60)
    
    if not jar_to_packages:
        print("No JAR files with packages found.")
    else:
        for jar_path in sorted(jar_to_packages.keys()):
            print(f"JAR: {jar_path}")
            for package_name in sorted(jar_to_packages[jar_path]):
                print(f"  - {package_name}")
            print()
    
    # Print summary
    total_packages = len(package_to_jars)
    total_jars = len(jar_to_packages)
    print(f"Summary: Found {total_packages} unique package names in {total_jars} JAR files.")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
