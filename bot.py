import os
import asyncio
import aiohttp
import urllib.parse
from ebooklib import epub
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from pyrogram.types import Message

# =========================================================
# CONFIGURATION & TOKENS
# =========================================================
# My.telegram.org se API_ID aur API_HASH prapt karein
# @BotFather se BOT_TOKEN prapt karein
API_ID = int(os.environ.get("API_ID", "35812810"))
API_HASH = os.environ.get("API_HASH", "6a6dc7b6e51d68c803e22a65dce7fd16")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8781074199:AAEH3ijwsacI6nnMevs3DRcUxw4wr7xGro0")

# Default Target Language: 'hi' (Hindi)
DEFAULT_TARGET_LANG = "hi"
MAX_CONCURRENT_REQUESTS = 15

# Custom Translation Token (Optional, agar paid API use kar rahe hain)
API_TOKEN = ""

# =========================================================

GOOGLE_FREE_URL = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={text}"

bot = Client("epub_translator_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def fetch_translation(session, text, target_lang="hi"):
    if not text or not text.strip():
        return text

    encoded_text = urllib.parse.quote(text)
    url = GOOGLE_FREE_URL.format(target_lang=target_lang, text=encoded_text)
    
    for attempt in range(3):
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return "".join([part[0] for part in data[0] if part and part[0]])
                elif response.status == 429:
                    await asyncio.sleep(1)
        except Exception:
            await asyncio.sleep(0.5)

    return text

async def translate_html_content(html_content, session, target_lang="hi"):
    soup = BeautifulSoup(html_content, 'html.parser')
    elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li', 'span'])
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def worker(elem):
        async with semaphore:
            original_text = elem.get_text().strip()
            if original_text and len(original_text) > 1:
                translated = await fetch_translation(session, original_text, target_lang)
                elem.string = translated

    tasks = [worker(elem) for elem in elements]
    await asyncio.gather(*tasks)
    return str(soup)

async def process_epub(input_path, output_path, target_lang="hi"):
    book = epub.read_epub(input_path)
    new_book = epub.EpubBook()
    
    titles = book.get_metadata('DC', 'title')
    orig_title = titles[0][0] if titles else "Novel"
    new_book.set_title(f"{orig_title} (Hindi)")
    new_book.set_language(target_lang)
    
    async with aiohttp.ClientSession() as session:
        for item in book.get_items():
            if item.get_type() == 9:  # ITEM_DOCUMENT (Chapters)
                content = item.get_content().decode('utf-8', errors='ignore')
                translated_html = await translate_html_content(content, session, target_lang)
                item.set_content(translated_html.encode('utf-8'))
                new_book.add_item(item)
            else:
                new_book.add_item(item)
                
    new_book.spine = book.spine
    epub.write_epub(output_path, new_book)

# =========================================================
# TELEGRAM BOT HANDLERS
# =========================================================

@bot.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    username = message.from_user.username or message.from_user.first_name
    await message.reply_text(
        f"👋 **Welcome @{username}!**\n\n"
        f"Mujhe koi bhi `.epub` file bhejo, main use ultra-fast speed se **Hindi** me translate karke wapas bhej dunga."
    )

@bot.on_message(filters.document)
async def handle_document(client: Client, message: Message):
    doc = message.document
    if not doc.file_name.endswith('.epub'):
        await message.reply_text("❌ Please send a valid `.epub` file.")
        return

    status_msg = await message.reply_text("📥 **Downloading EPUB file...**")
    
    input_path = f"downloads/{doc.file_name}"
    output_path = f"downloads/Hindi_{doc.file_name}"
    
    os.makedirs("downloads", exist_ok=True)
    
    try:
        await message.download(file_name=input_path)
        await status_msg.edit_text("⚡ **Translating EPUB to Hindi... Please wait.**")
        
        await process_epub(input_path, output_path, DEFAULT_TARGET_LANG)
        
        await status_msg.edit_text("📤 **Uploading translated file...**")
        await message.reply_document(
            document=output_path,
            caption=f"✅ **Translation Complete!**\n\n📄 **Original:** `{doc.file_name}`\n🌐 **Language:** Hindi"
        )
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error during translation:** `{str(e)}`")
        
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

if __name__ == "__main__":
    print("[🚀] Telegram EPUB Translator Bot Started...")
    bot.run()
