import argparse
import tennis_db
import sys

# Force utf-8 output to handle special characters in names
sys.stdout.reconfigure(encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description="Get player information by name.")
    parser.add_argument("name", help="Name of the player to search for")
    args = parser.parse_args()

    conn = tennis_db.get_connection()
    c = conn.cursor()
    
    # Use LIKE for partial matching
    c.execute("SELECT * FROM players WHERE name LIKE ?", (f"%{args.name}%",))
    rows = c.fetchall()
    columns = [d[0] for d in c.description]
    
    if not rows:
        print(f"No player found with name matching '{args.name}'")
    else:
        print(f"Found {len(rows)} player(s):")
        for row in rows:
            data = dict(zip(columns, row))
            print("-" * 20)
            print(f"Name: {data.get('name')}")
            print(f"ID: {data.get('player_id')}")
            print(f"Birth Date: {data.get('birth_date')}")
            print(f"Age: {data.get('age')}")
            print(f"Country: {data.get('country')}")
            print(f"College: {data.get('college')}")
            print(f"UTR Singles: {data.get('utr_singles')}")
            print(f"Updated At: {data.get('updated_at')}")
        print("-" * 20)

    conn.close()

if __name__ == "__main__":
    main()
