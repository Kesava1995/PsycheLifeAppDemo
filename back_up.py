import os
import shutil
from datetime import datetime

# Get the directory where the script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(BASE_DIR, 'instance', 'psychelife.db')
BACKUP_DIR = os.path.join(BASE_DIR, 'backup')

def run_backup():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = os.path.join(BACKUP_DIR, f'psychelife_backup_{timestamp}.db')
    
    if os.path.exists(SOURCE):
        shutil.copy2(SOURCE, destination)
        # Also keep a "latest" version for easy restoration
        shutil.copy2(SOURCE, os.path.join(BACKUP_DIR, 'psychelife_latest.db'))
        print(f"Backup successful: {destination}")
    else:
        print("Error: Source database not found in instance/ folder.")

if __name__ == "__main__":
    run_backup()
