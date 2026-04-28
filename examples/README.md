# Examples

Self-contained scripts demonstrating common geoimagery workflows.

| Script | What it shows |
|---|---|
| [`quickstart.py`](quickstart.py) | The 30-second tour: pick a polygon, list available NAIP dates, download a single GeoTIFF. |
| [`from_geojson.py`](from_geojson.py) | Batch workflow: read a GeoJSON of polygons, build an availability inventory, download every available month for every polygon. |

## Running an example

Each script is standalone. From the repo root:

```bash
pip install -e ".[all]"
earthengine authenticate                       # one time only
export GEE_PROJECT=your-gcp-project-id
python examples/quickstart.py
```

The scripts read your project ID from the `GEE_PROJECT` environment
variable so you don't accidentally commit it.
