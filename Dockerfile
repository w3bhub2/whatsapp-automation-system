FROM python:3.9-slim

# Install Chrome, Xvfb, and other dependencies
RUN apt-get update && \
    apt-get install -y wget gnupg unzip libgl1-mesa-dri curl fonts-liberation libappindicator3-1 libasound2 libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 libnspr4 libnss3 libxcomposite1 libxdamage1 libxrandr2 xdg-utils libxss1 libgtk-3-0 libgbm-dev libasound2-dev libnss3-dev xvfb && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-chrome.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# No additional dependencies needed

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install ChromeDriver using the selenium-manager (more reliable)
RUN pip install --no-cache-dir selenium==4.15.0 && \
    python -c "from selenium import webdriver; driver = webdriver.Chrome(options=webdriver.ChromeOptions())" || echo "ChromeDriver installed"

# Create directory for Chrome profile with open permissions
RUN mkdir -p /tmp/chrome-profile && chmod 777 /tmp/chrome-profile

# Set display environment variable
ENV DISPLAY=:99

# Copy application code
COPY worker.py .
COPY whatsapp_manager.py .
COPY pipedream_integration.py .
# Expose port
EXPOSE 8000

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
rm -f /tmp/.X99-lock\n\
Xvfb :99 -screen 0 1200x800x24 &\n\
python worker.py\n' > /entrypoint.sh && chmod +x /entrypoint.sh

# Run the application
ENTRYPOINT ["/entrypoint.sh"]