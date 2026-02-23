import os
import zipfile
import argparse
from datetime import datetime

def package_project(output_name=None, include_db=False):
    # Determine output filename
    if not output_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"courtside_deploy_{timestamp}.zip"
    
    if not output_name.endswith('.zip'):
        output_name += '.zip'

    # Project root (assumed current directory)
    root_dir = os.path.abspath(os.path.dirname(__file__))
    
    # Files/Dirs to exclude
    exclude_dirs = {
        '.git', '.gemini', 'node_modules', 'dist', 
        '__pycache__', '.venv', 'venv', 'deploy_temp', 'bck', 'output', 'scrape_output'
    }
    exclude_files = {
        output_name, 'tennis_data.db-shm', 'tennis_data.db-wal', 
        'package_project.py', 'find_hidden_d1.py', 'test_coverage_filter.py',
        'check_stats.py', 'verify_backfill.py', 'test_deploy.zip'
    }
    
    # If not including DB, add it to excluded files
    if not include_db:
        exclude_files.add('tennis_data.db')
        exclude_files.add('scrape_output.zip')

    print(f"Creating package: {output_name}")
    print(f"Include Database: {include_db}")
    print("Including Source Code, Population Scripts, and Documentation.")
    
    with zipfile.ZipFile(output_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(root_dir):
            # Prune directories in-place to avoid walking into them
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file in exclude_files:
                    continue
                
                # Logic for excluding large data while keeping source/config
                if not include_db:
                    if file.endswith(('.csv', '.jsonl', '.zip')):
                        # Keep requirements and essential configs
                        if file not in ['requirements.txt']:
                             continue

                file_path = os.path.join(root, file)
                archive_path = os.path.relpath(file_path, root_dir)
                
                print(f"  Adding: {archive_path}")
                zipf.write(file_path, archive_path)

    print(f"\nSuccessfully created {output_name}")
    print(f"Location: {os.path.abspath(output_name)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package CourtSide Analytics for deployment")
    parser.add_argument('--output', help='Output ZIP filename')
    parser.add_argument('--include-db', action='store_true', help='Include the large tennis_data.db file')
    
    args = parser.parse_args()
    package_project(args.output, args.include_db)
