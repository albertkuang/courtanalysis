# UTR Player Scraper

This tool allows you to scrape player data from the Universal Tennis Rating (UTR) website based on specific filters.

## Prerequisites

- Python 3.x
- A valid UTR account (email and password)

## Installation

1.  Navigate to the directory:
    ```bash
    cd c:\work\github\tennis
    ```

2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the script using Python:

```bash
python scraper.py
```

Follow the on-screen prompts to enter your credentials. The script is currently configured to search for:
-   **Nationality**: Canada (CAN)
-   **Gender**: Female (F)
-   **UTR**: Greater than 8.0

## Notes

-   The script acts as a standard user client (`User-Agent` mocked as Chrome).
-   Frequent automated requests might trigger rate limits or security checks. Use responsibly.
-   "Junior" status is not explicitly filtered at the API level in this version but can be inferred from the results or added if specific age parameters are identified.
