import pandas as pd
import sqlite3
import os

def import_junior_finalists():
    csv_file = 'itf_junior_finalists_10years.csv'
    db_file = 'tennis_data.db'
    
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found.")
        return
        
    print(f"Loading {csv_file}...")
    df = pd.read_csv(csv_file)
    
    # Rename columns to match UI expectations
    rename_map = {
        'loser_id': 'finalist_id',
        'loser_name': 'finalist_name',
        'loser_utr': 'finalist_utr',
        'loser_rank': 'finalist_rank'
    }
    df = df.rename(columns=rename_map)
    
    # Basic cleaning
    df['date'] = df['date'].fillna('')
    df['tournament'] = df['tournament'].fillna('Unknown Tournament')
    df['score'] = df['score'].fillna('')
    
    # Handle numbers
    df['winner_utr'] = pd.to_numeric(df['winner_utr'], errors='coerce')
    df['finalist_utr'] = pd.to_numeric(df['finalist_utr'], errors='coerce')
    df['winner_rank'] = pd.to_numeric(df['winner_rank'], errors='coerce')
    df['finalist_rank'] = pd.to_numeric(df['finalist_rank'], errors='coerce')
    
    # Keep only relevant columns for the table
    cols = ['date', 'tournament', 'round', 'score', 
            'winner_id', 'winner_name', 'winner_utr', 'winner_rank',
            'finalist_id', 'finalist_name', 'finalist_utr', 'finalist_rank']
    
    # Ensure all columns exist
    for col in cols:
        if col not in df.columns:
            df[col] = None
            
    final_df = df[cols]
    
    print(f"Importing {len(final_df)} records into {db_file}...")
    
    conn = sqlite3.connect(db_file)
    final_df.to_sql('junior_finalists', conn, if_exists='replace', index=False)
    
    # Create indexes for performance
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_junior_finalists_date ON junior_finalists(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_junior_finalists_winner ON junior_finalists(winner_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_junior_finalists_finalist ON junior_finalists(finalist_id)")
    
    conn.commit()
    conn.close()
    print("Import complete.")

if __name__ == "__main__":
    import_junior_finalists()
    
