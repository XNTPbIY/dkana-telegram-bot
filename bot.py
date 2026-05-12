import requests
import time
import random
import json

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8703098869:AAGANurvwhEfO8gAFr0Q5l6Dbpi2Q-YdsDo"
DKANA_API_KEY = "5c6275a18b4bc810e9f2d70db41c4f51"
DKANA_API_URL = "https://udkana.ru/api/v1"
# ====================

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
last_update_id = 0
feed_cache = []
current_page = 1
ITEMS_PER_PAGE = 5

def send_message(chat_id, text, reply_markup=None):
    url = f"{BASE_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = reply_markup
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        print(f"Ошибка: {e}")

def get_feed(limit=100):
    url = f"{DKANA_API_URL}/feed?limit={limit}&api_key={DKANA_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json().get("feed", [])
    except Exception as e:
        print(f"Ошибка get_feed: {e}")
    return []

def get_recipe_by_id(recipe_id):
    for item in feed_cache:
        if item.get("id") == recipe_id:
            return item
    return None

def show_recipe(chat_id, recipe_id):
    item = get_recipe_by_id(recipe_id)
    if not item:
        send_message(chat_id, "❌ Рецепт не найден")
        return
    
    recipe = item.get("recipe", {})
    author = item.get("author_nickname", item.get("author_email", "Пользователь"))
    
    text = f"🍲 <b>{recipe.get('name', 'Без названия')}</b>\n\n"
    text += f"👤 Автор: {author}\n"
    text += f"❤️ Лайков: {item.get('likes', 0)}\n\n"
    text += f"📌 <b>Тип:</b> {recipe.get('type', 'Не указан')}\n\n"
    
    ings = recipe.get("ingredients", [])
    if ings:
        text += "<b>🛒 Ингредиенты:</b>\n"
        for ing in ings[:8]:
            text += f"• {ing['name']}: {ing['amount']} {ing['unit']}\n"
        if len(ings) > 8:
            text += "...\n"
        text += "\n"
    
    desc = recipe.get("description", "")
    if desc:
        text += f"<b>📖 Приготовление:</b>\n{desc[:500]}"
        if len(desc) > 500:
            text += "..."
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "◀ Назад в ленту", "callback_data": f"page_{current_page}"}],
            [{"text": "🏠 Главное меню", "callback_data": "menu"}]
        ]
    }
    send_message(chat_id, text, keyboard)

def refresh_feed_cache():
    global feed_cache
    feed_cache = get_feed(100)
    return feed_cache

def show_feed_page(chat_id, page):
    global feed_cache, current_page
    if not feed_cache:
        feed_cache = refresh_feed_cache()
    
    if not feed_cache:
        send_message(chat_id, "📭 Лента пока пуста")
        return
    
    total_items = len(feed_cache)
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages
    
    current_page = page
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = feed_cache[start:end]
    
    keyboard = {"inline_keyboard": []}
    
    for i, item in enumerate(page_items):
        name = item.get("recipe", {}).get("name", "Без названия")[:35]
        keyboard["inline_keyboard"].append([{"text": f"{start + i + 1}. {name}", "callback_data": f"item_{item.get('id')}"}])
    
    nav_row = []
    if page > 1:
        nav_row.append({"text": "◀ Назад", "callback_data": f"page_{page - 1}"})
    if page < total_pages:
        nav_row.append({"text": "Вперед ▶", "callback_data": f"page_{page + 1}"})
    if nav_row:
        keyboard["inline_keyboard"].append(nav_row)
    
    keyboard["inline_keyboard"].append([{"text": "🏠 Главное меню", "callback_data": "menu"}])
    
    send_message(chat_id, f"📖 <b>Лента рецептов</b> — стр. {page} из {total_pages} (всего {total_items})", keyboard)

print("🚀 Бот запущен!")

if __name__ == "__main__":
    last_update_id = 0
    
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
                                    [{"text": "📖 Лента", "callback_data": "list"}],
                                    [{"text": "🎲 Случайный рецепт", "callback_data": "random"}]
                                ]
                            }
                            send_message(chat_id, "🍳 <b>Главное меню</b>", kb)
                        elif data == "list":
                            feed_cache = refresh_feed_cache()
                            show_feed_page(chat_id, 1)
                        elif data == "random":
                            if not feed_cache:
                                feed_cache = refresh_feed_cache()
                            if feed_cache:
                                item = random.choice(feed_cache)
                                show_recipe(chat_id, item.get("id"))
                            else:
                                send_message(chat_id, "📭 Лента пуста")
                        elif data.startswith("page_"):
                            page = int(data.split("_")[1])
                            show_feed_page(chat_id, page)
                        elif data.startswith("item_"):
                            rid = data.split("_")[1]
                            show_recipe(chat_id, rid)
                    
                    elif "message" in update:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"].get("text", "")
                        chat_type = update["message"]["chat"].get("type", "")
                        
                        if chat_type == "channel":
                            continue
                        
                        if text == "/start":
                            kb = {
                                "inline_keyboard": [
                                    [{"text": "📖 Лента", "callback_data": "list"}],
                                    [{"text": "🎲 Случайный рецепт", "callback_data": "random"}]
                                ]
                            }
                            send_message(chat_id, "🍳 <b>Добро пожаловать в DKana бот!</b>", kb)
                        elif text == "/feed":
                            feed_cache = refresh_feed_cache()
                            show_feed_page(chat_id, 1)
                        elif text == "/random":
                            if not feed_cache:
                                feed_cache = refresh_feed_cache()
                            if feed_cache:
                                item = random.choice(feed_cache)
                                show_recipe(chat_id, item.get("id"))
                            else:
                                send_message(chat_id, "📭 Лента пуста")
                        elif text == "/help":
                            send_message(chat_id, "🍳 <b>Команды</b>\n\n/start - Главное меню\n/feed - Лента рецептов\n/random - Случайный рецепт")
            
        except Exception as e:
            print(f"Ошибка: {e}")
        
        time.sleep(1)
