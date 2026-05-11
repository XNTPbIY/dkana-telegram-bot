import requests
import time
import random
import hashlib

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8703098869:AAGANurvwhEfO8gAFr0Q5l6Dbpi2Q-YdsDo"
DKANA_API_KEY = "5c6275a18b4bc810e9f2d70db41c4f51"
DKANA_API_URL = "https://udkana.ru/api/v1"
CHANNEL_ID = "@ваш_канал"  # ID канала
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
    """Получает рецепты из Общей ленты"""
    url = f"{DKANA_API_URL}/feed?limit={limit}&api_key={DKANA_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("feed", [])
    except Exception as e:
        print(f"Ошибка: {e}")
    return []

def get_random_from_feed():
    feed = get_feed(50)
    if feed:
        return random.choice(feed)
    return None

def get_photo_url(item):
    """Получает первую фотографию"""
    photo_urls = item.get("photo_urls", [])
    if photo_urls:
        return photo_urls[0]
    
    recipe = item.get("recipe", {})
    photos = recipe.get("photos", [])
    if photos and photos[0].startswith("http"):
        return photos[0]
    return None

def format_full_recipe(item):
    """Форматирует ПОЛНЫЙ рецепт с описанием и кнопкой"""
    recipe = item.get("recipe", {})
    author = item.get("author_nickname", item.get("author_email", "Пользователь"))
    share_id = item.get("share_id", "")
    
    # Полный текст рецепта
    text = f"🍲 <b>{recipe.get('name', 'Без названия')}</b>\n"
    text += f"👤 <i>Автор: {author}</i>\n"
    text += f"❤️ Лайков: {item.get('likes', 0)}\n\n"
    
    text += f"📌 <b>Тип:</b> {recipe.get('type', 'Не указан')}\n\n"
    
    # Все ингредиенты
    ingredients = recipe.get("ingredients", [])
    if ingredients:
        text += "<b>🛒 Ингредиенты:</b>\n"
        for ing in ingredients:
            text += f"• {ing['name']}: {ing['amount']} {ing['unit']}\n"
        text += "\n"
    
    # Полное описание (шаги)
    description = recipe.get("description", "")
    if description:
        text += "<b>📖 Приготовление:</b>\n"
        text += description
        text += "\n\n"
    
    # Заметки
    notes = recipe.get("notes", "")
    if notes:
        text += f"<b>📌 Заметки:</b>\n{notes}\n\n"
    
    # Кнопка для просмотра на сайте
    site_url = f"https://udkana.ru/?import={share_id}" if share_id else "https://udkana.ru/"
    
    return text, site_url

def create_recipe_keyboard(site_url):
    """Клавиатура с кнопкой для открытия рецепта"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔗 Открыть рецепт на сайте", "url": site_url}],
            [{"text": "🏠 Главное меню", "callback_data": "menu"}]
        ]
    }
    return keyboard

def send_to_channel(item):
    """Отправляет новый рецепт в канал"""
    recipe = item.get("recipe", {})
    author = item.get("author_nickname", item.get("author_email", "Пользователь"))
    share_id = item.get("share_id", "")
    photo = get_photo_url(item)
    
    site_url = f"https://udkana.ru/?import={share_id}" if share_id else "https://udkana.ru/"
    
    caption = f"🍲 <b>НОВЫЙ РЕЦЕПТ В ЛЕНТЕ!</b>\n\n"
    caption += f"🍳 <b>{recipe.get('name', 'Без названия')}</b>\n"
    caption += f"👤 Автор: {author}\n"
    caption += f"📌 {recipe.get('type', '')}\n\n"
    caption += f"🔗 <a href='{site_url}'>Открыть рецепт</a>"
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔗 Открыть рецепт", "url": site_url}]
        ]
    }
    
    if photo:
        send_photo(CHANNEL_ID, photo, caption, keyboard)
    else:
        send_message(CHANNEL_ID, caption, keyboard)
    print(f"✅ Новый рецепт отправлен в канал: {recipe.get('name')}")

def check_new_recipes():
    global last_recipes_hash
    
    feed = get_feed(5)
    if not feed:
        return
    
    current_hash = hashlib.md5(str(feed).encode()).hexdigest()
    
    if last_recipes_hash and last_recipes_hash != current_hash:
        send_to_channel(feed[0])
    
    last_recipes_hash = current_hash

def create_list_keyboard(feed, page, per_page=5):
    total_pages = (len(feed) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    page_feed = feed[start:end]
    
    keyboard = []
    for i, item in enumerate(page_feed):
        recipe = item.get("recipe", {})
        name = recipe.get("name", "Без названия")[:30]
        actual_num = start + i + 1
        keyboard.append([{"text": f"{actual_num}. {name}", "callback_data": f"item_{item['id']}"}])
    
    nav_row = []
    if page > 1:
        nav_row.append({"text": "◀ Назад", "callback_data": f"page_{page - 1}"})
    if page < total_pages:
        nav_row.append({"text": "Вперед ▶", "callback_data": f"page_{page + 1}"})
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([{"text": "🏠 Главное меню", "callback_data": "menu"}])
    return {"inline_keyboard": keyboard}

def create_menu_keyboard():
    keyboard = {
        "inline_keyboard": [
            [{"text": "📖 Лента рецептов", "callback_data": "list_1"}],
            [{"text": "🎲 Случайный рецепт", "callback_data": "random"}],
            [{"text": "❓ Помощь", "callback_data": "help"}],
            [{"text": "📢 Наш канал", "url": "https://t.me/udekana"}]
        ]
    }
    return keyboard

print("🚀 Бот запущен!")

if __name__ == "__main__":
    feed_cache = []
    cache_time = 0
    
    while True:
        try:
            current_time = time.time()
            
            if current_time - last_check_time > 300:
                check_new_recipes()
                last_check_time = current_time
            
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
                        
                        if time.time() - cache_time > 300 or not feed_cache:
                            feed_cache = get_feed(100)
                            cache_time = time.time()
                        
                        callback_url = f"{BASE_URL}/answerCallbackQuery"
                        requests.post(callback_url, json={"callback_query_id": query["id"]})
                        
                        if data == "menu":
                            send_message(chat_id, "🍳 <b>Главное меню</b>", create_menu_keyboard())
                        elif data == "help":
                            send_message(chat_id, "🍳 <b>Команды бота</b>\n\n/start - Главное меню\n/feed - Лента рецептов\n/random - Случайный рецепт\n\n📢 Наш канал: https://t.me/udekana", create_menu_keyboard())
                        elif data == "random":
                            item = get_random_from_feed()
                            if item:
                                text, site_url = format_full_recipe(item)
                                keyboard = create_recipe_keyboard(site_url)
                                photo = get_photo_url(item)
                                if photo:
                                    send_photo(chat_id, photo, text, keyboard)
                                else:
                                    send_message(chat_id, text, keyboard)
                            else:
                                send_message(chat_id, "📭 Лента пока пуста", create_menu_keyboard())
                        elif data.startswith("list_"):
                            page = int(data.split("_")[1])
                            if feed_cache:
                                send_message(chat_id, f"📖 <b>Лента рецептов</b> — страница {page} (всего {len(feed_cache)})", create_list_keyboard(feed_cache, page))
                        elif data.startswith("item_"):
                            item_id = data.split("_")[1]
                            for item in feed_cache:
                                if item.get("id") == item_id:
                                    text, site_url = format_full_recipe(item)
                                    keyboard = create_recipe_keyboard(site_url)
                                    photo = get_photo_url(item)
                                    if photo:
                                        send_photo(chat_id, photo, text, keyboard)
                                    else:
                                        send_message(chat_id, text, keyboard)
                                    break
                        elif data.startswith("page_"):
                            page = int(data.split("_")[1])
                            if feed_cache:
                                send_message(chat_id, f"📖 <b>Лента рецептов</b> — страница {page}", create_list_keyboard(feed_cache, page))
                    
                    elif "message" in update:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"].get("text", "")
                        
                        if text == "/start":
                            send_message(chat_id, "🍳 <b>Добро пожаловать в DKana бот!</b>\n\nСамые вкусные рецепты из общей ленты", create_menu_keyboard())
                        elif text == "/feed":
                            feed_cache = get_feed(100)
                            cache_time = time.time()
                            if feed_cache:
                                send_message(chat_id, f"📖 <b>Лента рецептов</b> (всего {len(feed_cache)})", create_list_keyboard(feed_cache, 1))
                            else:
                                send_message(chat_id, "📭 Лента пока пуста\n\nОпубликуйте свой первый рецепт!", create_menu_keyboard())
                        elif text == "/random":
                            item = get_random_from_feed()
                            if item:
                                text, site_url = format_full_recipe(item)
                                keyboard = create_recipe_keyboard(site_url)
                                photo = get_photo_url(item)
                                if photo:
                                    send_photo(chat_id, photo, text, keyboard)
                                else:
                                    send_message(chat_id, text, keyboard)
                            else:
                                send_message(chat_id, "📭 Лента пока пуста", create_menu_keyboard())
                        elif text == "/help":
                            send_message(chat_id, "🍳 <b>Команды</b>\n\n/feed - Лента рецептов\n/random - Случайный рецепт\n/start - Главное меню\n\n📢 Наш канал: https://t.me/udekana", create_menu_keyboard())
                        else:
                            send_message(chat_id, "❓ Неизвестная команда. Используйте /help", create_menu_keyboard())
            
        except Exception as e:
            print(f"Ошибка: {e}")
        
        time.sleep(1)
