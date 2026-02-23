
import os

api_file = 'api.py'

with open(api_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the new implementations
new_search = """@app.get("/college/search")
def search_colleges_endpoint(query: str = None, division: str = 'D1'):
    \"\"\"Search for colleges.\"\"\"
    print(f"API: Searching for {query}")
    import importlib
    import college_service
    try:
        importlib.reload(college_service)
        results = college_service.search_colleges(query, division)
        print(f"API: Found {len(results)} results")
        return {"data": results}
    except Exception as e:
        print(f"API: College Search Error: {e}")
        import traceback
        traceback.print_exc()
        return {"data": [], "error": str(e)}"""

new_roster = """@app.get("/college/{club_id}/roster")
def get_college_roster_endpoint(club_id: str, gender: str = 'M'):
    \"\"\"Get roster for a college.\"\"\"
    print(f"API: Roster for {club_id}")
    import importlib
    import college_service
    try:
        importlib.reload(college_service)
        roster = college_service.get_roster(club_id, gender)
        print(f"API: Roster count {len(roster)}")
        return {"data": roster}
    except Exception as e:
        print(f"API: Roster Error: {e}")
        import traceback
        traceback.print_exc()
        return {"data": [], "error": str(e)}"""

# Original strings to replace (using exact substrings from the view_file output)
# Note: Indentation is 4 spaces.

orig_search = """@app.get("/college/search")
def search_colleges_endpoint(query: str = None, division: str = 'D1'):
    \"\"\"Search for colleges.\"\"\"
    return {"data": college_service.search_colleges(query, division)}"""

orig_roster = """@app.get("/college/{club_id}/roster")
def get_college_roster_endpoint(club_id: str, gender: str = 'M'):
    \"\"\"Get roster for a college.\"\"\"
    return {"data": college_service.get_roster(club_id, gender)}"""

# Replace
if orig_search in content:
    content = content.replace(orig_search, new_search)
    print("Replaced search endpoint")
else:
    print("Could not find search endpoint string")

if orig_roster in content:
    content = content.replace(orig_roster, new_roster)
    print("Replaced roster endpoint")
else:
    print("Could not find roster endpoint string")

with open(api_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Finished patching api.py")
