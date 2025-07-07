import requests
import cairosvg
from flask import Flask, send_file
from bs4 import BeautifulSoup
from PIL import Image 

app = Flask(__name__)
url = "https://www.meteoromania.ro/avertizari/"

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
    if tag:
        img = tag.find("img")
        if img and img.has_attr("src"):
            image_url = img["src"]
            response = requests.get(image_url)
            if response.status_code == 200:
                with open("temp.png", "wb") as png_file:
                    cairosvg.svg2png(bytestring=response.content, write_to=png_file)
                img = Image.open("temp.png").convert("RGB")
                img.save("output.bmp")
            return send_file("output.bmp", mimetype="image/bmp")
        else:
            return "Nu exista imagine2"
    else:
        return "Nu exista imagine1"
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
