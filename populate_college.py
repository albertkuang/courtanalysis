import subprocess
import sys

def populate_college_players():
    """
    Runs the import_players.py script for major tennis nations to populate college player data.
    """
    # List of countries with significant number of players in US Colleges
    countries = [
        "USA", "CAN", "GBR", "ESP", "FRA", "ITA", "AUS", "GER", 
        "ARG", "BRA", "SWE", "JPN", "CHN", "IND"
    ]
    
    country_arg = ",".join(countries)
    
    print(f"Starting College Player Population for: {country_arg}")
    
    cmd = [
        sys.executable, "-u",
        "import_players.py", 
        "--category", "college", 
        "--country", country_arg,
        "--workers", "10"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("\nPopulation complete!")
    except subprocess.CalledProcessError as e:
        print(f"\nError running population script: {e}")

if __name__ == "__main__":
    populate_college_players()
