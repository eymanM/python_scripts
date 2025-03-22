#!/usr/bin/env python3
"""
Java File Text Searcher

A script that recursively searches for .java files and then searches for 
specified text within those files. Implemented with asynchronous operations
for improved performance.
"""

import os
import re
import sys
import asyncio
import argparse
from pathlib import Path
from typing import List, Tuple, Set, Dict
import time


class JavaTextSearcher:
    def __init__(self, search_text: str, root_dir: str = '.', case_sensitive: bool = False):
        """
        Initialize the Java text searcher.
        
        Args:
            search_text: The text to search for within .java files
            root_dir: The root directory to begin the recursive search from
            case_sensitive: Whether the search should be case sensitive
        """
        self.search_text = search_text
        self.root_dir = root_dir
        self.case_sensitive = case_sensitive
        self.results: Dict[str, List[Tuple[int, str]]] = {}
        self.java_files: List[Path] = []

    async def find_java_files(self) -> List[Path]:
        """
        Asynchronously find all .java files recursively starting from root_dir.
        
        Returns:
            List of Path objects for all found .java files
        """
        print(f"Searching for .java files in {self.root_dir}...")
        
        # This operation is I/O bound, so we'll run it in a thread pool
        loop = asyncio.get_running_loop()
        self.java_files = await loop.run_in_executor(
            None,
            self._find_java_files_sync
        )
        
        print(f"Found {len(self.java_files)} .java files")
        return self.java_files
    
    def _find_java_files_sync(self) -> List[Path]:
        """Synchronous helper for finding .java files"""
        java_files = []
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                if file.endswith('.java'):
                    java_files.append(Path(root) / file)
        return java_files

    async def search_file(self, file_path: Path) -> Tuple[Path, List[Tuple[int, str]]]:
        """
        Search for the specified text in a single file.
        
        Args:
            file_path: Path to the file to search within
            
        Returns:
            Tuple of (file_path, list of (line_number, line_content) matches)
        """
        try:
            # Run file reading and searching in a thread pool
            loop = asyncio.get_running_loop()
            matches = await loop.run_in_executor(
                None,
                self._search_file_sync,
                file_path
            )
            return file_path, matches
        except Exception as e:
            print(f"Error searching file {file_path}: {str(e)}")
            return file_path, []
    
    def _search_file_sync(self, file_path: Path) -> List[Tuple[int, str]]:
        """Synchronous helper for searching text in a file"""
        matches = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    if self._line_contains_text(line):
                        matches.append((i, line.strip()))
        except UnicodeDecodeError:
            # Try with a different encoding if UTF-8 fails
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    for i, line in enumerate(f, 1):
                        if self._line_contains_text(line):
                            matches.append((i, line.strip()))
            except Exception:
                pass  # Skip files that cannot be read
        except Exception:
            pass  # Skip files that cannot be read for other reasons
            
        return matches

    def _line_contains_text(self, line: str) -> bool:
        """Check if a line contains the search text, respecting case sensitivity setting"""
        if self.case_sensitive:
            return self.search_text in line
        else:
            return self.search_text.lower() in line.lower()

    async def search_all_files(self) -> Dict[str, List[Tuple[int, str]]]:
        """
        Search for the specified text in all found .java files.
        
        Returns:
            Dictionary mapping file paths to lists of (line_number, line_content) matches
        """
        if not self.java_files:
            await self.find_java_files()
            
        if not self.java_files:
            print("No .java files found to search")
            return {}
            
        print(f"Searching for '{self.search_text}' in {len(self.java_files)} files...")
        start_time = time.time()
        
        # Create a list of tasks for all files
        tasks = [self.search_file(file) for file in self.java_files]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # Process results
        for file_path, matches in results:
            if matches:  # Only include files with matches
                self.results[str(file_path)] = matches
                
        elapsed = time.time() - start_time
        match_count = sum(len(matches) for matches in self.results.values())
        print(f"Search completed in {elapsed:.2f} seconds")
        print(f"Found {match_count} matches in {len(self.results)} files")
        
        return self.results

    def display_results(self) -> None:
        """Display search results in a readable format"""
        if not self.results:
            print("No matches found.")
            return
            
        for file_path, matches in self.results.items():
            print(f"\n{file_path} ({len(matches)} matches):")
            print("-" * 80)
            for line_num, line in matches:
                print(f"{line_num:5d}: {line}")
            print("-" * 80)


async def main():
    parser = argparse.ArgumentParser(description='Search for text in .java files recursively')
    parser.add_argument('search_text', help='Text to search for')
    parser.add_argument('--dir', '-d', default='.', help='Root directory to start search from (default: current directory)')
    parser.add_argument('--case-sensitive', '-c', action='store_true', help='Perform case-sensitive search')
    
    args = parser.parse_args()
    
    searcher = JavaTextSearcher(
        search_text=args.search_text,
        root_dir=args.dir,
        case_sensitive=args.case_sensitive
    )
    
    await searcher.find_java_files()
    await searcher.search_all_files()
    searcher.display_results()


if __name__ == "__main__":
    # Run the async main function
    if sys.platform.startswith('win'):
        # Windows-specific event loop policy
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
