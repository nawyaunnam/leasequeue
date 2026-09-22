# Public data and provenance

`snapshot.json` contains a captured public-data response (or the fields needed
by this project). `live-report.json` contains the derived results. Acquisition
timestamps and exact endpoint URLs are present in both. A snapshot is historical
as soon as it is captured; run `python3 live.py` to refresh it.

The original-code MIT license does not relicense third-party data. Respect the
source terms and rate limits when collecting or reusing data.

- USGS: https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php
  Earthquake observations can be revised after publication. No hazard forecast is implied.
- GitHub: https://docs.github.com/en/rest/activity/events
  Public events may lag by 30 seconds to six hours. Repository search is indexed data.
  Issue titles and maintainer labels are public third-party content, attributed by URL.
- Open-Meteo: https://open-meteo.com/en/docs
  Attribution: Open-Meteo, CC BY 4.0. Weather-model data can include forecasts and estimates.
- Open Library: https://openlibrary.org/dev/docs/api/search
  Bibliographic records are catalog metadata, not retailer inventory.

Only the source URLs listed in this project's report are used by its live workflow.
No private GitHub data, credentials, API keys, or personal user files are included.
