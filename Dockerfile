FROM python:3.11-slim

ENV OPENAI_API_KEY = your_API_key

WORKDIR /coverLetterTool

RUN chmod -R 777 /coverLetterTool

RUN apt-get update && \
    apt-get install -y curl unzip wget gnupg2&& \
    apt-get install -y fonts-liberation libnss3 libxss1 libasound2 libatk-bridge2.0-0 libgtk-3-0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

    # Install LaTeX and related packages
RUN apt-get update && apt-get install -y \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-xetex \
    latexmk \
    make \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN apt-get update && \
    wget -O /usr/share/keyrings/google-chrome.gpg https://dl.google.com/linux/linux_signing_key.pub && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable
# Install ChromeDriver
#RUN wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/118.0.5993.70/chromedriver_linux64.zip" && \
#    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
#    rm /tmp/chromedriver.zip

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-u", "app.py"]

EXPOSE 5000