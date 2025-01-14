from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
import PySimpleGUI as sg
import re
from PIL import Image
from anticaptchaofficial.imagecaptcha import imagecaptcha
from twocaptchaapi import TwoCaptchaApi
from bs4 import BeautifulSoup
import json
import base64
import os
import sys


def captcha_builder_manual(resp):
    with open('captcha.svg', 'w') as f:
        f.write(re.sub('(<path d=)(.*?)(fill="none"/>)', '', resp['captcha']))

    drawing = svg2rlg('captcha.svg')
    renderPM.drawToFile(drawing, "captcha.png", fmt="PNG")

    im = Image.open('captcha.png')
    im = im.convert('RGB').convert('P', palette=Image.ADAPTIVE)
    im.save('captcha.gif')

    layout = [[sg.Image('captcha.gif')],
              [sg.Text("Enter Captcha Below")],
              [sg.Input(key='input')],
              [sg.Button('Submit', bind_return_key=True)]]

    window = sg.Window('Enter Captcha', layout, finalize=True)
    window.TKroot.focus_force()  # focus on window
    window.Element('input').SetFocus()  # focus on field
    window.BringToFront()
    event, values = window.read()
    window.close()
    return values['input']


def captcha_builder_api(resp, api_key, which_captcha):
    with open('captcha.svg', 'w') as f:
        f.write(re.sub('(<path d=)(.*?)(fill=\"none\"/>)', '', resp['captcha']))

    drawing = svg2rlg('captcha.svg')
    renderPM.drawToFile(drawing, "captcha.png", fmt="PNG")

    if which_captcha == '0':  # anticaptchaofficial
        solver = imagecaptcha()
        solver.set_verbose(1)
        solver.set_key(api_key)
        captcha_text = solver.solve_and_return_solution("captcha.png")

    elif which_captcha == '1':  # twocaptchaapi
        api = TwoCaptchaApi(api_key)
        captcha_predicted = api.solve("captcha.png")
        captcha_text = captcha_predicted.await_result()
    else:
        print("Invalid captcha API choice")
    if captcha_text != 0:
        print(f"Captcha text: {captcha_text}")
    else:
        print(f"Task finished with error: {solver.error_code}")
    return captcha_text


def captcha_builder_auto(resp):
    model = open(os.path.join(os.path.dirname(sys.argv[0]), "model.txt")).read()
    svg_data = resp['captcha']
    soup = BeautifulSoup(svg_data, 'html.parser')
    model = json.loads(base64.b64decode(model.encode('ascii')))
    CAPTCHA = {}

    for path in soup.find_all('path', {'fill': re.compile("#")}):
        ENCODED_STRING = path.get('d').upper()
        INDEX = re.findall('M(\d+)', ENCODED_STRING)[0]
        ENCODED_STRING = re.findall("([A-Z])", ENCODED_STRING)
        ENCODED_STRING = "".join(ENCODED_STRING)
        CAPTCHA[int(INDEX)] = model.get(ENCODED_STRING)

    CAPTCHA = sorted(CAPTCHA.items())
    CAPTCHA_STRING = ''

    for char in CAPTCHA:
        CAPTCHA_STRING += char[1]
    return CAPTCHA_STRING
