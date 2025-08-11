import requests
import cairosvg
import io
import struct
import re
from flask import Flask, send_file, Response
from bs4 import BeautifulSoup
from PIL import Image

app = Flask(__name__)
url_avertizari = "https://www.meteoromania.ro/avertizari/"
AVERTIZARI_FILE = "avertizari_data.bin"
img_URLS = []

judete_ascii = [
    "Alba", "Arad", "Arges", "Bacau", "Bihor", "Bistrita-Nasaud", "Botosani",
    "Brasov", "Braila", "Buzau", "Caras-Severin", "Calarasi", "Cluj", "Constanta",
    "Covasna", "Dambovita", "Dolj", "Galati", "Giurgiu", "Gorj", "Harghita",
    "Hunedoara", "Ialomita", "Iasi", "Ilfov", "Maramures", "Mehedinti", "Mures",
    "Neamt", "Olt", "Prahova", "Satu Mare", "Salaj", "Sibiu", "Suceava",
    "Teleorman", "Timis", "Tulcea", "Vaslui", "Valcea", "Vrancea", "Bucuresti"
]
county_pattern = r"\b("+ "|".join(re.escape(c) for c in judete_ascii) + r")\s+([A-Z])"

counties_pattern = "|".join(re.escape(c) for c in judete_ascii)
pattern = rf"\b(?!{counties_pattern}\b)([A-Za-z]+)\s+(?!{counties_pattern}\b)([A-Z][a-z]+)"
# https://www.meteoromania.ro/wp-content/plugins/meteo/json/imagini-radar.php
# pentru imagini radar
# https://maps.meteoromania.ro/hottest/7/72/46.png pentru harta

def rgb888_to_rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def clean_text(text):
    # Step 1: Replace sequences of 2+ spaces with a single space
    text = re.sub(r'\s{2,}', ' ', text)
    
    # Step 2: Insert newline between lowercase → Uppercase
    text = re.sub(r'([a-z0-9])([A-Z])', r'\1\n\2', text)
    
    text = re.sub(county_pattern, r"\1\n\2", text)
    
    # text = re.sub(pattern, r"\1\n\2", text)

    text = text.strip()
    # Step 3: Insert newline between digit → Uppercase

    # Step 4: Strip leading/trailing spaces

    return text

def romanian_to_ascii(text):
    replacements = {
        'ă': 'a', 'â': 'a', 'î': 'i',
        'ș': 's', 'ş': 's',  # note both s-comma and s-cedilla
        'ț': 't', 'ţ': 't',  # t-comma and t-cedilla
        'Ă': 'A', 'Â': 'A', 'Î': 'I',
        'Ș': 'S', 'Ş': 'S',
        'Ț': 'T', 'Ţ': 'T',
    }
    return ''.join(replacements.get(c, c) for c in text)

@app.route('/')
def index():
    return "This is the main page"

def send_image(image_url):
    response = requests.get(image_url)
    if response.status_code != 200:
        return "NO IMAGE"
    png_bytes = cairosvg.svg2png(bytestring=response.content)
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    pixels = img.load()
    width, height = img.size
    print(f"width: {width}, height : {height}")
    # sending data
    def generate():
        i = 0
        yield struct.pack(">H", width)
        yield struct.pack(">H", height)
        i += 4

        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                rgb565 = rgb888_to_rgb565(r, g, b)
                yield struct.pack(">H", rgb565)
                i += 2
                if i == 100000:
                    return
            
    
    return Response(generate(), mimetype='application/octet-stream')

@app.route('/page')
def get_page():
    with open(AVERTIZARI_FILE, "rb") as f:
        data = f.read()
    return Response(data, mimetype='application/octet-stream')

def fetch_image_avertizari(image_url):
    response = requests.get(image_url)
    if response.status_code != 200:
        return "NO IMAGE"
    png_bytes = cairosvg.svg2png(bytestring=response.content)
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    pixels = img.load()
    width, height = img.size
    print(f"width: {width}, height : {height}")
    pixels_565 = []

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            rgb565 = rgb888_to_rgb565(r, g, b)
            pixels_565.append(rgb565)
    return (width, height, pixels_565)


def fetch_text_avertizari(soup, fara_avertizari = False):
    avertizari_text = {}
    if not fara_avertizari:
        tds = soup.find_all("td", style=lambda s: s and "text-align:justify" in s)
       
        i = 0
        for td in tds:
            center_ps = td.find_all("p", attrs={"align": "center"})
            lines = []
            for p in center_ps:
                text = p.get_text(strip = True)
                ascii_text = romanian_to_ascii(text)
                ascii_text = clean_text(ascii_text)
                temp_lines = ascii_text.split('\n')
                for line in temp_lines:
                    lines.append(line)
            # print(lines)
            # print()
            important_text_coming = False
            for line in lines:
                # print(line)
                if important_text_coming:
                    avertizari_text.setdefault(i, "")
                    avertizari_text[i] += line + "\n"
                    important_text_coming = False
                    continue
                if "COD" in line or "Interval de valabilitate" in line or "Fenomene vizate" in line:
                    avertizari_text.setdefault(i, "")
                    avertizari_text[i] += line + "\n"

                if "Zone afectate" in line:
                    important_text_coming = True
            i += 1
    else:
        avertizari_text.setdefault(0, "Fara avertizari")

    return (len(avertizari_text), avertizari_text)



def fetch_and_write_avertizari():
    response = requests.get(url_avertizari)
    if (response.status_code != 200):
        return "Site-ul ANM nu a raspuns!"
    soup = BeautifulSoup(response.text, "html.parser")

    fara_avertizari = False
    tags = soup.find_all("div", class_="meteo_mapavertiz")
    if not tags:
        tags = soup.find("div", class_="avertizari")
        fara_avertizari = True
    for tag in tags:
        if tag:
            img = tag.find("img")
            if img and img.has_attr("src"):
                image_url = img["src"]
                if "https" not in image_url:
                    continue
                # print(image_url)
                # print(image_url)
                img_URLS.append(image_url)

    nr_avert, avertizari_txt = fetch_text_avertizari(soup, fara_avertizari)
    with open(AVERTIZARI_FILE, "wb") as f:
        f.write(struct.pack(">B", nr_avert))
        for i in range(nr_avert):
            f.write(struct.pack(">I", len(avertizari_txt[i])))
            f.write(avertizari_txt[i].encode("ascii", errors="replace"))
            width, height, pixels = fetch_image_avertizari(img_URLS[i])
            f.write(struct.pack(">H", width))
            f.write(struct.pack(">H", height))
            for pixel in pixels:
                f.write(struct.pack(">H", pixel))
                
fetch_and_write_avertizari()
if __name__ == "__main__":
    fetch_and_write_avertizari()
    app.run(debug=True)