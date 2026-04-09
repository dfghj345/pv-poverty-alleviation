# Seed Files

Default seed file layout used by `python data_pipeline/tools/load_seed_data.py`:

- `data_pipeline/seeds/city_location/city_location_seed.json`
- `data_pipeline/seeds/weather_radiation/weather_radiation_seed.json`
- `data_pipeline/seeds/policy_tariff/policy_tariff_seed.json`
- `data_pipeline/seeds/poverty_county/poverty_county_seed.json`
- `data_pipeline/seeds/cost/cost_seed.json`

Each dataset also supports `.csv` with the same basename.

JSON format:

```json
{
  "items": [
    {"province": "广东省", "city": "广州市", "latitude": 23.1291, "longitude": 113.2644}
  ]
}
```

CSV format:

```csv
province,city,latitude,longitude
广东省,广州市,23.1291,113.2644
```
