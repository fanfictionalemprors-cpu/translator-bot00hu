import asyncio
import aiohttp
import urllib.parse
import os
import sys
import glob
import argparse
from ebooklib import epub
from bs4 import BeautifulSoup

# =========================================================
# CONFIGURATION & TOKENS
# =========================================================
# Custom API Key / Token (Agar aapke paas Google Cloud Translation API,
# DeepL, ya kisi custom service ka Bearer Token hai to yahan dalein).
# Agar ise khali ("") chhodenge, to ye 100% FREE Google Engine use karega.
API_TOKEN = "8781074199:AAEH3ijwsacI6nnMevs3DRcUxw4wr7xGro0"  

# Default Target Language: 'hi' (Hindi)
DEFAULT_TARGET_LANG = "hi"

# Maximum Parallel Requests (Fast speed control)
MAX_CONCURRENT_REQUESTS = 15

# =========================================================

GOOGLE_FREE_URL = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={text}"
GOOGLE_PAID_API_URL = "https://translation.googleapis.com/language/translate/v2?key={api_key}"

async def fetch_translation(session, text, target_lang="hi", api_token=""):
    """
    Translates text snippet using Free Engine or Paid API Key if token provided.
    """
    if not text or not text.strip():
        return text

    # Scenario 1: Using Paid / Custom API Token
    if api_token:
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_token}" if not api_token.startswith("AIza") else ""
            }
            url = GOOGLE_PAID_API_URL.format(api_key=api_token) if api_token.startswith("AIza") else "YOUR_CUSTOM_ENDPOINT"
            payload = {
                "q": text,
                "target": target_lang,
                "format": "text"
            }
            async with session.post(url, json=payload, headers=headers, timeout=12) as resp:
                if resp.status == 200:
                    res_json = await resp.json()
                    return res_json['data']['translations'][0]['translatedText']
        except Exception:
            pass  # Fallback to Free Engine if Token fails

    # Scenario 2: Default Free Engine (Fast & Unlimited)
    encoded_text = urllib.parse.quote(text)
    url = GOOGLE_FREE_URL.format(target_lang=target_lang, text=encoded_text)
    
    for attempt in range(3):  # Retry logic for network stability
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    translated_text = "".join([part[0] for part in data[0] if part and part[0]])
                    return translated_text
                elif response.status == 429:
                    await asyncio.sleep(1)  # Cooldown on rate limit
        except Exception:
            await asyncio.sleep(0.5)

    return text  # Return original if all retries fail

async def translate_html_content(html_content, session, target_lang="hi", token=""):
    """
    Parses HTML content and translates paragraphs/headings concurrently.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li', 'span'])
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def worker(elem):
        async with semaphore:
            original_text = elem.get_text().strip()
            if original_text and len(original_text) > 1:
                translated = await fetch_translation(session, original_text, target_lang, api_token=token)
                elem.string = translated

    tasks = [worker(elem) for elem in elements]
    await asyncio.gather(*tasks)
    return str(soup)

async def process_epub(input_path, output_path, target_lang="hi", token=""):
    print(f"[⚡] Reading EPUB File: {input_path}")
    book = epub.read_epub(input_path)
    new_book = epub.EpubBook()
    
    # Preserve Title & Set Hindi Language Tag
    titles = book.get_metadata('DC', 'title')
    orig_title = titles[0][0] if titles else "Novel"
    new_book.set_title(f"{orig_title} (Hindi)")
    new_book.set_language(target_lang)
    
    async with aiohttp.ClientSession() as session:
        for item in book.get_items():
            if item.get_type() == 9:  # ITEM_DOCUMENT (Chapters/HTML content)
                print(f"[>] Translating Chapter: {item.get_name()}")
                content = item.get_content().decode('utf-8', errors='ignore')
                
                translated_html = await translate_html_content(content, session, target_lang, token)
                item.set_content(translated_html.encode('utf-8'))
                new_book.add_item(item)
            else:
                # Copy images, styles, fonts without modification
                new_book.add_item(item)
                
    new_book.spine = book.spine
    print(f"[✔] Saving Hindi EPUB to: {output_path}")
    epub.write_epub(output_path, new_book)
    print("[🎉] Translation Completed Successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fast Async Hindi EPUB Translator")
    parser.add_argument("-i", "--input", help="Input EPUB file path")
    parser.add_argument("-o", "--output", help="Output EPUB file path")
    parser.add_argument("-l", "--lang", default=DEFAULT_TARGET_LANG, help="Target language (Default: hi)")
    parser.add_argument("-t", "--token", default=API_TOKEN, help="Optional API Token/Key")
    
    args = parser.parse_args()
    
    input_file = args.input
    output_file = args.output
    
    # Render Auto-Detect Logic (Command Arguments Nahi Hone Par Bhi Chalega)
    if not input_file:
        epubs = glob.glob("*.epub")
        # Exclude output files if already generated
        epubs = [f for f in epubs if not f.startswith("translated_")]
        
        if epubs:
            input_file = epubs[0]
            print(f"[+] Auto-detected EPUB file in directory: {input_file}")
        else:
            print("[!] Error: No input `.epub` file found in root folder!")
            print("[!] Please add an .epub file to your project repository.")
            sys.exit(1)
            
    if not output_file:
        output_file = f"translated_{input_file}"
        
    asyncio.run(process_epub(input_file, output_file, args.lang, args.token))
