import re
import os

import requests
import urllib3
from bs4 import BeautifulSoup

# Centralized headers setup
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# Disable insecure request warnings globally to keep logs clean
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _make_request(url, stream=False, timeout=10):
    """Internal helper to make requests with SSL fallback and consistent headers"""
    try:
        return requests.get(url, timeout=timeout, headers=DEFAULT_HEADERS, stream=stream)
    except (requests.exceptions.SSLError, requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # Fallback to unverified for environments with SSL issues or slow cert verification
        return requests.get(url, verify=False, timeout=timeout, headers=DEFAULT_HEADERS, stream=stream)


def get_stations(icao):
    page = _make_request(f'https://www.liveatc.net/search/?icao={icao}')
    soup = BeautifulSoup(page.content, 'html.parser')

    stations = soup.find_all('table', class_='body', border='0', padding=lambda x: x != '0')
    freqs = soup.find_all('table', class_='freqTable', colspan='2')

    for table, freqs in zip(stations, freqs):
        title = table.find('strong').text
        up = table.find('font').text == 'UP'
        href = table.find('a', href=lambda x: x and x.startswith('/archive.php')).attrs['href']

        identifier = re.findall(r'/archive.php\?m=([a-zA-Z0-9_]+)', href)[0]

        frequencies = []
        rows = freqs.find_all('tr')[1:]
        for row in rows:
            cols = row.find_all('td')
            freq_title = cols[0].text
            freq_frequency = cols[1].text

            frequencies.append({'title': freq_title, 'frequency': freq_frequency})

        yield {'identifier': identifier, 'title': title, 'frequencies': frequencies, 'up': up}


def download_archive(station, date, time):
    page = _make_request(f'https://www.liveatc.net/archive.php?m={station}')
    archive_identifer = None

    if page.status_code == 200:
        soup = BeautifulSoup(page.content, 'html.parser')
        selected_option = soup.find('option', selected=True)
        if selected_option:
            archive_identifer = selected_option.attrs.get('value')

    # Fallback: Many stations follow the pattern 'kxyz1_app' -> 'KXYZ1-App'
    if not archive_identifer:
        print(f"  Warning: Could not scrape identifier for {station}, using fallback conversion...")
        parts = station.split('_')
        archive_identifer = '-'.join([p.capitalize() if i > 0 else p.upper() for i, p in enumerate(parts)])

    # Extract airport code from station identifier (e.g., 'kcho3_zdc_121675' -> 'kcho')
    station_prefix = station.split('_')[0]
    airport_code = re.sub(r'\d+$', '', station_prefix).lower()

    # https://archive.liveatc.net/kpdx/KPDX-App-Dep-Oct-01-2021-0000Z.mp3
    filename = f'{archive_identifer}-{date}-{time}.mp3'

    # Use system temp directory (cross-platform)
    import tempfile
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, filename)
    url = f'https://archive.liveatc.net/{airport_code}/{filename}'

    import time as time_module

    # Retry logic with exponential backoff
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Downloading: {url}")
            response = _make_request(url, stream=True, timeout=30)
            response.raise_for_status()

            # Write the file in chunks
            with open(path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return path

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1, 2, 4 seconds
                print(f"  Timeout/Connection error, retrying in {wait_time}s...")
                time_module.sleep(wait_time)
            else:
                raise Exception(f"Failed after {max_retries} attempts: {e}")
        except (requests.exceptions.HTTPError, Exception) as e:
            if "404" in str(e) or "403" in str(e):
                raise
            elif attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"  Error: {e}, retrying in {wait_time}s...")
                time_module.sleep(wait_time)
            else:
                raise


# download_archive('kpdx_zse', 'Oct-01-2021', '0000Z')
