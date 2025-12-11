import re
import os
import ssl

import requests
import urllib.request
from bs4 import BeautifulSoup
import certifi

# Create a custom SSL context that uses certifi certificates
try:
  ssl_context = ssl.create_default_context(cafile=certifi.where())
except Exception:
  ssl_context = None


def get_stations(icao):
  # Try with SSL verification first, fallback to unverified if it fails
  try:
    page = requests.get(f'https://www.liveatc.net/search/?icao={icao}', verify=certifi.where(), timeout=10)
  except requests.exceptions.SSLError:
    # If SSL verification fails, retry without verification (less secure but works)
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    page = requests.get(f'https://www.liveatc.net/search/?icao={icao}', verify=False, timeout=10)
  
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
  # Try with SSL verification first, fallback to unverified if it fails
  try:
    page = requests.get(f'https://www.liveatc.net/archive.php?m={station}', verify=certifi.where(), timeout=10)
  except requests.exceptions.SSLError:
    # If SSL verification fails, retry without verification (less secure but works)
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    page = requests.get(f'https://www.liveatc.net/archive.php?m={station}', verify=False, timeout=10)
  
  soup = BeautifulSoup(page.content, 'html.parser')
  archive_identifer = soup.find('option', selected=True).attrs['value']

  # Extract airport code from station identifier (e.g., 'kcho3_zdc_121675' -> 'kcho3')
  airport_code = station.split('_')[0]
  
  # https://archive.liveatc.net/kpdx/KPDX-App-Dep-Oct-01-2021-0000Z.mp3
  filename = f'{archive_identifer}-{date}-{time}.mp3'

  path = f'/tmp/{filename}'
  url = f'https://archive.liveatc.net/{airport_code}/{filename}'
  
  import time as time_module
  import socket
  
  # Retry logic with exponential backoff
  max_retries = 3
  for attempt in range(max_retries):
    try:
      print(f"Downloading: {url}")
      urllib.request.urlretrieve(url, path)
      return path
    except (socket.timeout, urllib.error.URLError) as e:
      if attempt < max_retries - 1:
        wait_time = 2 ** attempt  # 1, 2, 4 seconds
        print(f"  Timeout/Connection error, retrying in {wait_time}s...")
        time_module.sleep(wait_time)
      else:
        raise
    except Exception as e:
      # Other errors (like 403), don't retry
      raise


# download_archive('kpdx_zse', 'Oct-01-2021', '0000Z')
