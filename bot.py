import requests
import time
import random
import hashlib
import json

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8703098869:AAGANurvwhEfO8gAFr0Q5l6Dbpi2Q-YdsDo"
DKANA_API_KEY = "5c6275a18b4bc810e9f2d70db41c4f51"
DKANA_API_URL = "https://udkana.ru/api/v1"
CHANNEL_ID = "@udekana"
# ====================

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
last_update_id = 0
last_recipes_hash = ""
last_check_time = 0

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    url = f"{BASE_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        data["reply_markup"] = reply_markup
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        print(f"Ошибка: {e}")

def send_photo(chat_id, photo_url, caption, reply_markup=None):
    url = f"{BASE_URL}/sendPhoto"
    data = {"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = reply_markup
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        send_message(chat_id, caption, reply_markup)

def get_feed(limit=50):
    url = f"{DKANA_API_URL}/feed?limit={limit}&api_key={DKANA_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("feed", [])
    except Exception as e:
        print(f"Ошибка get_feed: {e}")
    return []

def create_magic_link(recipe):
    url = "https://udkana.ru/api.php?action=shareRecipe"
    clean_recipe = {
        "id": recipe.get("id"),
        "name": recipe.get("name"),
        "type": recipe.get("type", "Другое"),
        "ingredients": recipe.get("ingredients", []),
        "description": recipe.get("description", ""),
        "notes": recipe.get("notes", ""),
        "photos": recipe.get("photos", [])
    }
    try:
        r = requests.post(url, json={"recipe": clean_recipe}, timeout=10, headers={"Content-Type": "application/json"})
        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                return data.get("id")
    except:
        pass
    return None

def get_photo_url(item):
    photo_urls = item.get("photo_urls", [])
    if photo_urls:
        return photo_urls[0]
    recipe = item.get("recipe", {})
    photos = recipe.get("photos", [])
    if photos and photos[0].startswith("http"):
        return photos[0]
    return None

def random_from_feed():
    feed = get_feed(50)
    if feed:
        return random.choice(feed)
    return None

def show_recipe(chat_id, recipe_id):
    feed = get_feed(200)
    item = None
    for i in feed:
        if i.get("id") == recipe_id:
            item = i
            break
    
    if not item:
        send_message(chat_id, "❌ Рецепт не найден")
        return
    
    recipe = item.get("recipe", {})
    author = item.get("author_nickname", item.get("author_email", "Пользователь"))
    
    # Создаём ссылку
    share_id = item.get("share_id")
    if not share_id:
        share_id = create_magic_link(recipe)
    site_url = f"https://udkana.ru/?import={share_id}" if share_id else "https://udkana.ru/"
    
    # Текст
    text = f"🍲 <b>{recipe.get('name', 'Без названия')}</b>\n"
    text += f"👤 Автор: {author}\n"
    text += f"❤️ Лайков: {item.get('likes', 0)}\n\n"
    text += f"📌 Тип: {recipe.get('type', 'Не указан')}\n\n"
    
    ings = recipe.get("ingredients", [])
    if ings:
        text += "<b>🛒 Ингредиенты:</b>\n"
        for ing in ings[:10]:
            text += f"• {ing['name']}: {ing['amount']} {ing['unit']}\n"
        if len(ings) > 10:
            text += "...\n"
        text += "\n"
    
    desc = recipe.get("description", "")
    if desc:
        text += f"<b>📖 Приготовление:</b>\n{desc[:500]}\n"
        if len(desc) > 500:
            text += "...\n"
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔗 Открыть на сайте", "url": site_url}],
            [{"text": "🏠 Главное меню", "callback_data": "menu"}]
        ]
    }
    
    photo = get_photo_url(item)
    if photo:
        send_photo(chat_id, photo, text, keyboard)
    else:
        send_message(chat_id, text, keyboard)

print("🚀 Бот запущен!")

if __name__ == "__main__":
    feed_cache = []
    cache_time = 0
    
    while True:
        try:
            url = f"{BASE_URL}/getUpdates?offset={last_update_id + 1}&timeout=30"
            response = requests.get(url, timeout=35)
            
            if response.status_code == 200:
                updates = response.json().get("result", [])
                for update in updates:
                    last_update_id = update["update_id"]
                    
                    if "callback_query" in update:
                        query = update["callback_query"]
                        chat_id = query["message"]["chat"]["id"]
                        data = query["data"]
                        
                        requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": query["id"]})
                        
                        if data == "menu":
                            kb = {
                                "inline_keyboard": [
                                    [{"text": "📖 Лента", "callback_data": "list_1"}],
                                    [{"text": "🎲 Случайный", "callback_data": "random"}],
                                    [{"text": "❓ Помощь", "callback_data": "help"}]
                                ]
                            }
                            send_message(chat_id, "🍳 Главное меню", kb)
                        elif data == "help":
                            send_message(chat_id, "🍳 Команды:\n/start - меню\n/feed - лента\n/random - случайный рецепт")
                        elif data == "random":
                            item = random_from_feed()
                            if item:
                                show_recipe(chat_id, item.get("id"))
                            else:
                                send_message(chat_id, "📭 Лента пуста")
                        elif data.startswith("list_"):
                            feed_cache = get_feed(100)
                            if feed_cache:
                                kb = {"inline_keyboard": []}
                                for i, it in enumerate(feed_cache[:10]):
                                    name = it.get("recipe", {}).get("name", "Без названия")[:30]
                                    kb["inline_keyboard"].append([{"text": f"{i+1}. {name}", "callback_data": f"item_{it.get('id')}"}])
                                kb["inline_keyboard"].append([{"text": "🏠 Главное меню", "callback_data": "menu"}])
                                send_message(chat_id, f"📖 Лента (всего {len(feed_cache)} рец.)", kb)
                            else:
                                send_message(chat_id, "📭 Лента пуста")
                        elif data.startswith("item_"):
                            rid = data.split("_")[1]
                            show_recipe(chat_id, rid)
                    
                    elif "message" in update:
                        chat_id = update["message"]["chat"]["id"]
                        chat_type = update["message"]["chat"].get("type", "")
                        text = update["message"].get("text", "")
                        
                        if chat_type == "channel":
                            continue
                        
                        if text == "/start":
                            kb = {
                                "inline_keyboard": [
                                    [{"text": "📖 Лента", "callback_data": "list_1"}],
                                    [{"text": "🎲 Случайный", "callback_data": "random"}],
                                    [{"text": "❓ Помощь", "callback_data": "help"}]
                                ]
                            }
                            send_message(chat_id, "🍳 Добро пожаловать в DKana бот!", kb)
                        elif text == "/feed":
                            feed_cache = get_feed(100)
                            if feed_cache:
                                kb = {"inline_keyboard": []}
                                for i, it in enumerate(feed_cache[:10]):
                                    name = it.get("recipe", {}).get("name", "Без названия")[:30]
                                    kb["inline_keyboard"].append([{"text": f"{i+1}. {name}", "callback_data": f"item_{it.get('id')}"}])
                                kb["inline_keyboard"].append([{"text": "🏠 Главное меню", "callback_data": "menu"}])
                                send_message(chat_id, f"📖 Лента (всего {len(feed_cache)} рец.)", kb)
                            else:
                                send_message(chat_id, "📭 Лента пока пуста")
                        elif text == "/random":
                            item = random_from_feed()
                            if item:
                                show_recipe(chat_id, item.get("id"))
                            else:
                                send_message(chat_id, "📭 Лента пуста")
                        elif text == "/help":
                            send_message(chat_id, "🍳 Команды:\n/start - меню\n/feed - лента\n/random - случайный рецепт")
            
        except Exception as e:
            print(f"Ошибка: {e}")
        
        time.sleep(1)
