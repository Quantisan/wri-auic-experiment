# /// script
# requires-python = ">=3.12"
# dependencies = ["requests", "rasterio"]
# ///
"""nb4 spine check — does Cape Town COG coverage support city-wide suburb ranking?

Derives the baseline-vs-delta coverage asymmetry that anchors nb4 by measuring
three representative COGs and reading the AOI token for the rest:

  - The urban_extent baseline covers the metro (~1,334 km2), spanning ~150
    rankable OSM suburbs -> an informative ranking.
  - The business_district layers cover only the ~9 km2 CBD (~3-4 OSM suburbs)
    -> a degenerate ranking. Confirmed by opening one baseline and one delta;
    the other CBD deltas (cool roofs, park shade, ...) are classified by the
    business_district token alone, not opened here.

So goal-switching is structurally trivial (swap one COG URL, re-run the same
pipeline), but DATA COVERAGE -- not the algorithm -- is the binding constraint
on the delta goal. That asymmetry is nb4's central feasibility result.

Read-only: rasterio /vsicurl metadata reads on three COGs + Overpass.
Run: uv run exploration_notebooks/nb4_coverage_check.py
"""
import math
import time
import requests
import rasterio
from rasterio.warp import transform_bounds

S3 = "https://wri-cities-data-api.s3.us-east-1.amazonaws.com"
COG = f"{S3}/data/dev/utci/cog/"

# Public Overpass mirrors are flaky (504/429). Try them in turn before giving up.
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
]

# Three representative Cape Town COGs: the city-wide baseline, the CBD baseline,
# and a CBD-only delta. Their extents are the whole story.
COGS = {
    "business_district baseline":           "ZAF-Cape_Town__business_district__utci_1500_baseline__2023.tif",
    "urban_extent baseline":                "ZAF-Cape_Town__urban_extent__utci_1500_baseline__2023.tif",
    "business_district street_trees delta": "ZAF-Cape_Town__business_district__utci_1500_street_trees_achievable_vs_baseline__2023.tif",
}


def cog_extent(url):
    """Return (wgs84_bbox, area_km2, width_px, height_px) for a COG."""
    with rasterio.open(f"/vsicurl/{url}") as src:
        w = transform_bounds(src.crs, "EPSG:4326", *src.bounds)  # (W, S, E, N)
        lat_mid = (w[1] + w[3]) / 2
        width_km = (w[2] - w[0]) * 111 * math.cos(math.radians(lat_mid))
        height_km = (w[3] - w[1]) * 111
        return w, width_km * height_km, src.width, src.height


def suburbs_in(bbox):
    """OSM place=suburb elements within bbox = (S, W, N, E), with centroids.

    Overpass rejects naive POSTs (406) -- form-encode the query and send a
    User-Agent. Most suburb polygons are multipolygon relations.
    """
    query = (
        f'[out:json][timeout:90];('
        f'way["place"="suburb"]{bbox};'
        f'relation["place"="suburb"]{bbox};'
        f'node["place"="suburb"]{bbox};);out tags center;'
    )
    headers = {"User-Agent": "wri-auic-experiment/0.1"}
    last_error = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            resp = requests.post(endpoint, data={"data": query},
                                 headers=headers, timeout=120)
            resp.raise_for_status()
            return resp.json()["elements"]
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(2)
    raise RuntimeError(f"All Overpass endpoints failed; last error: {last_error}")


def centroid_in_box(element, bbox):
    """True if an OSM element's centroid falls within bbox = (W, S, E, N)."""
    c = element.get("center") or {"lon": element.get("lon"), "lat": element.get("lat")}
    return (
        c["lon"] is not None
        and bbox[0] <= c["lon"] <= bbox[2]
        and bbox[1] <= c["lat"] <= bbox[3]
    )


def main():
    # 1. COG extents
    extents = {}
    print("COG extents (WGS84):")
    for label, fname in COGS.items():
        bbox, area_km2, width_px, height_px = cog_extent(COG + fname)
        extents[label] = bbox
        print(f"  {label:40s} {area_km2:8.1f} km2  {width_px}x{height_px}px")

    # 2. OSM suburbs across the metro extent vs. inside the CBD extent
    mw = extents["urban_extent baseline"]               # (W, S, E, N)
    metro = suburbs_in((mw[1], mw[0], mw[3], mw[2]))     # (S, W, N, E)
    polygons = [e for e in metro if e["type"] in ("way", "relation")]

    cw = extents["business_district baseline"]           # (W, S, E, N)
    cbd = sorted({
        e.get("tags", {}).get("name")
        for e in metro
        if centroid_in_box(e, cw)
    })

    print(f"\nOSM place=suburb in metro extent: {len(metro)} "
          f"({len(polygons)} polygon-capable)")
    print(f"OSM place=suburb in CBD extent:   {len(cbd)} -> {cbd}")

    print("\nFinding: baseline ranks city-wide (~150 suburbs); every delta COG "
          "is CBD-only (~3-4 suburbs). Coverage, not algorithm, is the limit.")


if __name__ == "__main__":
    main()
