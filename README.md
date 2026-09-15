# [Eve market-anomaly prediction](https://eve-market-anomaly.streamlit.app/)

A prediction dashboard For the Online Economics Game [Eve Online](https://www.eveonline.com/) built to allow real time item overview and anomaly detection directly from [Jita Trade Hub](https://wiki.eveuniversity.org/Trade_hubs) providing helpfull support for in game trading decisons.

## What does it do

- Retrives the Eve online market data directly from the [Eve_JSON_API](https://esi.evetech.net/meta/openapi.json?compatibility_date=2026-08-18) into a PostgreSQL(now Supabase) database
- Runs the retreived data through an Isolation Forrest algoroith to for anomaly detection
- Displays the item overview and anomaly data/tables to a shipped [streamlit.io](https://streamlit.io/) Dashboard

## Tech Stack/Libraries

- Python: Used for the base project code(JSON fetches, anomaly detection). 
    - Pandas 
    - numpy 
    - sklearn 
    - sqlalchemy 
    - streamlit 
    - plotly 
- PostgreSQL: used for initial local database
- Supabase: used later to replace local DB

## Usage/Notes

User makes use of a Simple sidebar search of the item's name then proceeds to receive.
- An overview of the item
- past price hitory of the item
- past volume hitory if the item
- All anomalies for the selected item
- Top anomolies across all items