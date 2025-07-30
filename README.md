# Temu Scraper

A powerful and user-friendly web scraping tool for extracting product data from Temu.com with advanced features to avoid detection.

## Overview

Temu Scraper is a Python application that uses Playwright and a stealth module to navigate and extract product information from Temu's e-commerce platform. The tool features a graphical user interface (GUI) built with Tkinter, making it accessible to users without programming experience.

## Features

- **User-friendly GUI**: Easy-to-use interface for configuring scraping parameters
- **Search Query Customization**: Specify what products to search for
- **Anti-Detection Measures**:
  - Human-like interactions (random delays, mouse movements)
  - Stealth mode to bypass bot detection
  - Configurable time intervals between actions
  - Built-in retry mechanism with exponential backoff
- **Proxy Support**: Use proxy servers to avoid IP blocking
- **Session Persistence**: Save and reuse login sessions
- **CAPTCHA Handling**: Interactive prompts when CAPTCHA challenges appear
- **Real-time Progress Tracking**: Live logs and progress indicators
- **Data Export**: Save results to CSV files for further analysis
- **Safe Interruption**: Stop and save results at any time

## Requirements

- Python 3.7+
- Playwright
- playwright-stealth
- Tkinter (usually included with Python)

Install dependencies using:

```bash
pip install -r requirements.txt
```

## Usage

1. **Launch the application**:
   ```bash
   python temu_scraper_gui.py
   ```

2. **Configure scraping parameters**:
   - Enter your search query (e.g., "men's shoes", "women's dresses")
   - Set interval timing (min/max minutes between actions)
   - Configure cooldown frequency (pauses after N requests)
   - Enable proxy if needed and provide proxy server details (format: IP:PORT)
   - Choose whether to save login sessions
   - Select output CSV file location

3. **Start scraping**:
   - Click "Start Scraping" to begin the process
   - A browser window will open automatically for login/solving CAPTCHA
   - Click "I'm Ready" after completing login/solving CAPTCHA
   - Solve CAPTCHAs when prompted and click "CAPTCHA Solved" when ready to continue
   - Monitor progress in the logs section

4. **View and save results**:
   - Products are automatically saved to the specified CSV file
   - Click "Stop & Save" at any time to halt scraping
   - Results include product details like name, price, ratings, and more

## How It Works

The scraper operates in the following sequence:

1. **Initialization**: Opens a browser session with stealth mode to avoid detection
2. **Login**: Waits for the user to log in manually or uses saved session data
3. **Search**: Submits the search query and waits for results
4. **Data Extraction**: Intercepts API responses to extract product information
5. **Pagination**: Automatically clicks "See more" to load additional products
6. **Result Processing**: Parses and saves product data to CSV

The tool uses network interception to capture API responses directly, rather than parsing HTML, providing more reliable data extraction.

## Advanced Features

### Session Management

- **Save Sessions**: Maintain login state between runs
- **Clear Sessions**: Remove saved credentials when needed

### Proxy Configuration

Format: host:port

### Timing Controls

- **Min/Max Intervals**: Random delays between actions to appear human-like
- **Cooldown Frequency**: Adds longer pauses after specified number of requests

## Troubleshooting

- **429 Errors**: The scraper automatically implements retry logic with increasing delays
- **CAPTCHA Challenges**: Follow the on-screen instructions to solve CAPTCHAs when prompted
- **Connection Issues**: Try using a proxy server if you encounter connection problems

## Notes

- This tool is for educational purposes only
- Use responsibly and in accordance with Temu's terms of service
- Rate limiting is implemented to avoid overloading the website
