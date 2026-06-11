import click
import os
import requests
import uuid
import time

from tqdm import tqdm


# Use correct bbox order: (left, bottom, right, top)
BOUNDING_BOXES = {
    'ile-de-france': (-0.06592, 47.76887, 5.07568, 49.58223),
    'paris': (2.18628, 48.80234, 2.50763, 48.91528),
    'lyon': (4.67434, 45.69803, 4.99569, 45.81779),
    'bourg-saint-maurice': (6.44005, 45.54387, 7.08275, 45.78381),
    'londres': (-0.489,51.28,0.236,51.686)
}


def format_requests(bbox, offset=0, pages=10):
    base_url = "https://api.openstreetmap.org/api/0.6/trackpoints"
    left, bottom, right, top = bbox

    urls = []
    for page in range(offset, offset + pages):
        url = f"{base_url}?bbox={left},{bottom},{right},{top}&page={page}"
        urls.append(url)

    return urls


def save_gpx(content, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content.decode("utf-8"))


@click.command()
@click.option('--pages', default=2, help='Number of pages to fetch')
@click.option('--city', default='paris', help='City name')
@click.option('--output_dir', default='gpx_traces', help='Output directory')
@click.option('--offset', default=0, help='Pagination offset')
@click.option('--delay', default=1.0, help='Delay between requests (seconds)')
def collect_traces(pages, city, offset, output_dir, delay):

    city = city.lower()

    if city not in BOUNDING_BOXES:
        raise ValueError(f"Unknown city: {city}")

    os.makedirs(output_dir, exist_ok=True)

    urls = format_requests(BOUNDING_BOXES[city], offset, pages)

    for url in tqdm(urls):
        try:
            r = requests.get(url, timeout=30)

            if r.status_code != 200:
                print(f"Failed: {r.status_code}")
                continue

            filename = f"trace_{city}_{uuid.uuid4()}.gpx"
            path = os.path.join(output_dir, filename)

            save_gpx(r.content, path)

        except requests.RequestException as e:
            print(f"Request error: {e}")

        time.sleep(delay)  # be nice to OSM


if __name__ == '__main__':
    collect_traces()