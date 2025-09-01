import bs4
import flask
import flask_bcrypt
import flask_login
import flask_sqlalchemy
import jinja2
import openai
import requests
import selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import sqlalchemy
import subprocess


print("All packages imported successfully!")
subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "test.tex"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
    )

options = Options()
options.add_argument('--headless')  # Remove this line to see the browser
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(options=options)
driver.get('https://www.google.com')
print(driver.title)
driver.quit()