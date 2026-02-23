
def create_user(conn, user_data):
    """
    Create a new user.
    user_data: dict with email, password_hash, (optional google_id, name)
    """
    sql = '''
    INSERT INTO users (email, password_hash, google_id, name)
    VALUES (?, ?, ?, ?)
    '''
    try:
        cur = conn.cursor()
        cur.execute(sql, (
            user_data.get('email'),
            user_data.get('password_hash'),
            user_data.get('google_id'),
            user_data.get('name')
        ))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None # Email exists
    except Exception as e:
        print(f"Error creating user: {e}")
        return None

def get_user_by_email(conn, email):
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    if row:
        return dict(row)
    return None
