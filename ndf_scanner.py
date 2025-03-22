import os
import base64
import xml.etree.ElementTree as ET
from argparse import ArgumentParser

def decode_wm_property(original_base64_str):
    try:
        # Add padding if missing (base64 requirement)
        missing_padding = len(original_base64_str) % 4
        if missing_padding:
            original_base64_str += '=' * (4 - missing_padding)
            
        decoded_bytes = base64.b64decode(original_base64_str)
        text_parts = []
        buffer = bytearray()
        
        for i in range(0, len(decoded_bytes), 2):
            if i+1 < len(decoded_bytes) and decoded_bytes[i+1] == 0:
                buffer.append(decoded_bytes[i])
            elif buffer:
                text_parts.append(buffer.decode('utf-8', errors='ignore'))
                buffer.clear()
        
        return ''.join(text_parts)
    
    except Exception as e:
        return f"Decoding failed: {str(e)}"


def scan_ndf_files(root_dir, search_str):
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.ndf'):
                file_path = os.path.join(root, file)
                try:
                    tree = ET.parse(file_path)
                    root_elem = tree.getroot()
                    
                    # Find IRTNODE_PROPERTY element
                    prop = root_elem.find(".//value[@name='IRTNODE_PROPERTY']")
                    if prop is not None and prop.text:
                        decoded = decode_wm_property(prop.text)
                        
                        if search_str.lower() in decoded.lower().replace('\n', ''):
                            print(f"Match found in: {file_path}")
                            print(f"Decoded content fragment:\n{decoded[:200]}...\n")
                            
                except (ET.ParseError, UnicodeDecodeError) as e:
                    continue;
                except Exception as e:
                    print(f"Unexpected error with {file_path}: {str(e)}")


if __name__ == "__main__":
    # parser = ArgumentParser(description='Scan .ndf files for encoded patterns')
    # parser.add_argument('root_dir', help='Root directory to search')
    # parser.add_argument('search_str', help='String to search in decoded content')
    # args = parser.parse_args()
    #scan_ndf_files(args.root_dir, args.search_str)

    scan_ndf_files(r"C:\Users\STEFANOWICZM\Downloads\package_2025-02-17", "plat_raport_zalaczniki")
