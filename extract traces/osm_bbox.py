import click
import os
import requests
import uuid
import time

from tqdm import tqdm


BOUNDING_BOXES = {
    'ile-de-france': (-0.06592, 47.76887, 5.07568, 49.58223),
    'paris': (2.18628, 48.80234, 2.50763, 48.91528),
    'londres': (-0.489, 51.28, 0.236, 51.686),
    'beijing': (116.04, 39.76, 116.64, 40.16)
}


def split_bbox(bbox, step):
    left, bottom, right, top = bbox
    boxes = []

    x = left
    while x < right:
        y = bottom
        while y < top:
            boxes.append((
                x,
                y,
                min(x + step, right),
                min(y + step, top)
            ))
            y += step
        x += step

    return boxes


def build_url(bbox, page):
    base_url = "https://api.openstreetmap.org/api/0.6/trackpoints"
    left, bottom, right, top = bbox
    return f"{base_url}?bbox={left},{bottom},{right},{top}&page={page}"


def save_gpx(content, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content.decode("utf-8"))


@click.command()
@click.option('--pages', default=2, help='Pages per tile (keep small!)')
@click.option('--city', default='londres', help='City name')
@click.option('--output_dir', default='gpx_traces', help='Output directory')
@click.option('--offset', default=0, help='Pagination offset')
@click.option('--delay', default=1.0, help='Delay between requests')
@click.option('--tile_size', default=0.02, help='Tile size (degrees)')
def collect_traces(pages, city, offset, output_dir, delay, tile_size):

    city = city.lower()

    if city not in BOUNDING_BOXES:
        raise ValueError(f"Unknown city: {city}")

    os.makedirs(output_dir, exist_ok=True)

    bbox = BOUNDING_BOXES[city]
    tiles = split_bbox(bbox, tile_size)

    print(f"Total tiles: {len(tiles)}")

    for tile in tqdm(tiles, desc="Tiles"):
        for page in range(offset, offset + pages):

            url = build_url(tile, page)

            try:
                r = requests.get(url, timeout=30)

                if r.status_code != 200:
                    print(f"Tile failed (page {page}): {r.status_code}")
                    break  # stop paging this tile

                if not r.content.strip():
                    break  # no more data for this tile

                filename = f"trace_{city}_{uuid.uuid4()}.gpx"
                path = os.path.join(output_dir, filename)

                save_gpx(r.content, path)

            except requests.RequestException as e:
                print(f"Request error: {e}")
                break

            time.sleep(delay)
if __name__ == '__main__':
    collect_traces()