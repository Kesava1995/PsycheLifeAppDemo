import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_LATEST = os.path.join(BASE_DIR, 'backup', 'psychelife_latest.db')
DESTINATION = os.path.join(BASE_DIR, 'instance', 'psychelife.db')

def run_restore():
    if not os.path.exists(os.path.dirname(DESTINATION)):
        os.makedirs(os.path.dirname(DESTINATION))
        
    if os.path.exists(BACKUP_LATEST):
        shutil.copy2(BACKUP_LATEST, DESTINATION)
        print("Database restored successfully from latest backup.")
    else:
        print("Error: No backup file found in backup/psychelife_latest.db")

if __name__ == "__main__":
    run_restore()
