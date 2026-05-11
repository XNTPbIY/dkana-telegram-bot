import requests
import time
import random
import hashlib

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8703098869:AAGANurvwhEfO8gAFr0Q5l6Dbpi2Q-YdsDo"
DKANA_API_KEY = "5c6275a18b4bc810e9f2d70db41c4f51"
DKANA_API_URL = "https://udkana.ru/api/v1"
CHANNEL_ID = "@udekana"  # ЗАМЕНИ НА ID КАНАЛА (например @dkana_recipes или -1001234567890)
# ====================

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
last_update_id = 0
last_feed_hash = ""
last_check_time = 0

def send_message(chat_id, text, reply_markup=None):
    url = f"{BASE_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = reply_markup
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def send_photo(chat_id, photo_url, caption):
    url = f"{BASE_URL}/sendPhoto"
    data = {"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        send_message(chat_id, caption)

def get_feed(limit=50):
    """Получает рецепты из Общей ленты"""
    url = f"{DKANA_API_URL}/feed?limit={limit}&api_key={DKANA_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("feed", [])
    except Exception as e:
        print(f"Ошибка получения ленты: {e}")
    return []

def get_random_from_feed():
    feed = get_feed(50)
    if feed:
        return random.choice(feed)
    return None

def get_photo_url(item):
    """Получает первую фотографию из записи ленты"""
    photo_urls = item.get("photo_urls", [])
    if photo_urls:
        return photo_urls[0]
    
    recipe = item.get("recipe", {})
    photos = recipe.get("photos", [])
    if photos:
        first_photo = photos[0]
        if first_photo.startswith("http"):
            return first_photo
    return None

def format_feed_item(item):
    """Форматирует запись из ленты в красивое сообщение"""
    recipe = item.get("recipe", {})
    author = item.get("author_nickname", item.get("author_email", "Пользователь"))
    
    text = f"🍲 <b>{recipe.get('name', 'Без названия')}</b>\n"
    text += f"👤 <i>Автор: {author}</i>\n"
    text += f"❤️ Лайков: {item.get('likes', 0)}\n\n"
    
    text += f"📌 <b>Тип:</b> {recipe.get('type', 'Не указан')}\n\n"
    
    ingredients = recipe.get("ingredients", [])
    if ingredients:
        text += "<b>🛒 Ингредиенты:</b>\n"
        for ing in ingredients[:10]:
            text += f"• {ing['name']}: {ing['amount']} {ing['unit']}\n"
        if len(ingredients) > 10:
            text += f"... и ещё {len(ingredients) - 10} ингредиентов\n"
    
    description = recipe.get("description", "")
    if description:
        desc = description[:300]
        if len(description) > 300:
            desc += "..."
        text += f"\n<b>📖 {desc}</b>\n"
    
    text += f"\n🔗 <a href='https://udkana.ru/'>В гостях у DKana</a>"
    
    return text

def send_to_channel(item):
    """Отправляет новый рецепт в канал"""
    recipe = item.get("recipe", {})
    author = item.get("author_nickname", item.get("author_email", "Пользователь"))
    photo = get_photo_url(item)
    
    caption = f"🍲 <b>НОВЫЙ РЕЦЕПТ В ЛЕНТЕ!</b>\n\n"
    caption += f"🍳 <b>{recipe.get('name', 'Без названия')}</b>\n"
    caption += f"👤 Автор: {author}\n"
    caption += f"❤️ Лайков: {item.get('likes', 0)}\n\n"
    caption += f"📌 {recipe.get('type', '')}\n\n"
    caption += f"🔗 <a href='https://udkana.ru/'>Смотреть на сайте</a>"
    
    if photo:
        send_photo(CHANNEL_ID, photo, caption)
    else:
        send_message(CHANNEL_ID, caption)
    print(f"✅ Новый рецепт отправлен в канал: {recipe.get('name')}")

def check_new_recipes():
    """Проверяет появление новых рецептов в ленте"""
    global last_feed_hash
    
    feed = get_feed(10)
    if not feed:
        return
    
    # Создаём хеш последних рецептов
    current_hash = hashlib.md5(str(feed).encode()).hexdigest()
    
    if last_feed_hash and last_feed_hash != current_hash:
        # Появились новые рецепты!
        new_recipe = feed[0]  # Самый новый
        send_to_channel(new_recipe)
    
    last_feed_hash = current_hash

def create_keyboard(feed, page, per_page=5):
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
    keyboard = [
        [{"text": "📖 Лента рецептов", "callback_data": "list_1"}],
        [{"text": "🎲 Случайный рецепт", "callback_data": "random"}],
        [{"text": "❓ Помощь", "callback_data": "help"}]
    ]
    return {"inline_keyboard": keyboard}

print("🚀 Бот запущен! Лента рецептов + авто-постинг в канал")

if __name__ == "__main__":
    feed_cache = []
    cache_time = 0
    
    while True:
        try:
            current_time = time.time()
            
            # Проверяем новые рецепты каждые 5 минут (300 секунд)
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
                            send_message(chat_id, "🍳 <b>Главное меню</b>\n\nВыберите действие:", create_menu_keyboard())
                        elif data == "help":
                            send_message(chat_id, "🍳 <b>Помощь</b>\n\n/start - запуск бота\n/feed - лента рецептов\n/random - случайный рецепт", create_menu_keyboard())
                        elif data == "random":
                            item = get_random_from_feed()
                            if item:
                                photo = get_photo_url(item)
                                caption = format_feed_item(item)
                                if photo:
                                    send_photo(chat_id, photo, caption)
                                else:
                                    send_message(chat_id, caption)
                            else:
                                send_message(chat_id, "❌ Лента пуста")
                        elif data.startswith("list_"):
                            page = int(data.split("_")[1])
                            if feed_cache:
                                send_message(chat_id, f"📖 <b>Лента рецептов</b> — страница {page} (всего {len(feed_cache)})", create_keyboard(feed_cache, page))
                        elif data.startswith("item_"):
                            item_id = data.split("_")[1]
                            for item in feed_cache:
                                if item.get("id") == item_id:
                                    photo = get_photo_url(item)
                                    caption = format_feed_item(item)
                                    if photo:
                                        send_photo(chat_id, photo, caption)
                                    else:
                                        send_message(chat_id, caption)
                                    break
                        elif data.startswith("page_"):
                            page = int(data.split("_")[1])
                            if feed_cache:
                                send_message(chat_id, f"📖 <b>Лента рецептов</b> — страница {page}", create_keyboard(feed_cache, page))
                    
                    elif "message" in update:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"].get("text", "")
                        
                        if text == "/start":
                            send_message(chat_id, "🍳 <b>Добро пожаловать в DKana бот!</b>\n\nСамые вкусные рецепты из общей ленты", create_menu_keyboard())
                        elif text == "/feed":
                            feed_cache = get_feed(100)
                            cache_time = time.time()
                            if feed_cache:
                                send_message(chat_id, f"📖 <b>Лента рецептов</b> (всего {len(feed_cache)}) — страница 1", create_keyboard(feed_cache, 1))
                            else:
                                send_message(chat_id, "📭 Лента пока пуста")
                        elif text == "/random":
                            item = get_random_from_feed()
                            if item:
                                photo = get_photo_url(item)
                                caption = format_feed_item(item)
                                if photo:
                                    send_photo(chat_id, photo, caption)
                                else:
                                    send_message(chat_id, caption)
                            else:
                                send_message(chat_id, "❌ Лента пуста")
                        elif text == "/help":
                            send_message(chat_id, "🍳 <b>Команды:</b>\n/feed - лента рецептов\n/random - случайный рецепт\n/start - главное меню")
                        else:
                            send_message(chat_id, "❓ Неизвестная команда. Используйте /help", create_menu_keyboard())
            
        except Exception as e:
            print(f"Ошибка: {e}")
        
        time.sleep(1)
