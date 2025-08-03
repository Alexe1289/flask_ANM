import requests
import cairosvg
import io
import struct
from flask import Flask, send_file, Response
from bs4 import BeautifulSoup
from PIL import Image

app = Flask(__name__)
url = "https://www.meteoromania.ro/avertizari/"


def rgb888_to_rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

@app.route('/')
def index():
    return "This is the main page"

@app.route('/page')
def get_page():
    harti = ""
    response = requests.get(url)
    if (response.status_code != 200):
        return "Site-ul ANM nu a raspuns!"
    avertizari = response.text
    soup = BeautifulSoup(avertizari, "html.parser")

    tag = soup.find("div", class_="meteo_mapavertiz")
    if not tag:
        tag = soup.find("div", class_="avertizari")
        if not tag:
            return "Nu exista avertizari"
    img = tag.find("img")
    if img and img.has_attr("src"):
        image_url = img["src"]
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
    else:
        return "Nu exista imagine2"
    # tags = soup.find_all("div", class_="meteo_mapavertiz")
    # for tag in tags:
    #     if tag:
    #         img = tag.find("img")
    #         if img and img.has_attr("src"):
    #             image_url = img["src"]
    #             harti += image_url
    #             harti += "\n"
    #         else:
    #             return "Nu exista imagine2"
    #     else:
    #         return "Nu exista imagine1"
    # return harti

if __name__ == "__main__":
    app.run(debug=True)