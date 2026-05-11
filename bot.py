import requests
import time
import random

# ===== НАСТРОЙКИ (ВПИШИ СВОИ ЗНАЧЕНИЯ) =====
BOT_TOKEN = "8703098869:AAGANurvwhEfO8gAFr0Q5l6Dbpi2Q-YdsDo"
DKANA_API_KEY = "5c6275a18b4bc810e9f2d70db41c4f51"  # Например: a1b2c3d4e5f6g7h8i9j0...
DKANA_API_URL = "https://udkana.ru/api/v1"
# =========================================

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
last_update_id = 0

# Хранилище состояний пользователей
user_states = {}

def send_message(chat_id, text, reply_markup=None):
    url = f"{BASE_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = reply_markup
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        print(f"Ошибка: {e}")

def send_photo(chat_id, photo_url, caption):
    url = f"{BASE_URL}/sendPhoto"
    data = {"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        send_message(chat_id, caption)

def get_recipes():
    url = f"{DKANA_API_URL}/recipes?limit=100&api_key={DKANA_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json().get("recipes", [])
    except Exception as e:
        print(f"Ошибка: {e}")
    return []

def get_random_recipe():
    url = f"{DKANA_API_URL}/recipes?limit=50&api_key={DKANA_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            recipes = r.json().get("recipes", [])
            if recipes:
                return random.choice(recipes)
    except Exception as e:
        print(f"Ошибка: {e}")
    return None

def get_photo_url(recipe):
    photos = recipe.get("photos", [])
    if photos:
        first_photo = photos[0]
        if first_photo.startswith("http"):
            return first_photo
    return None

def format_recipe_full(recipe):
    text = f"🍲 <b>{recipe['name']}</b>\n"
    text += f"📌 <i>{recipe['type']}</i>\n\n"
    
    text += "<b>🛒 Ингредиенты:</b>\n"
    for ing in recipe.get("ingredients", [])[:15]:
        text += f"• {ing['name']}: {ing['amount']} {ing['unit']}\n"
    
    if len(recipe.get("ingredients", [])) > 15:
        text += f"... и ещё {len(recipe['ingredients']) - 15} ингредиентов\n"
    
    if recipe.get("description"):
        desc = recipe['description'][:500]
        if len(recipe['description']) > 500:
            desc += "..."
        text += f"\n<b>📖 Приготовление:</b>\n{desc}\n"
    
    text += f"\n🔗 <a href='https://udkana.ru/'>В гостях у DKana</a>"
    return text

def create_menu_keyboard():
    keyboard = [
        [{"text": "📖 Список рецептов", "callback_data": "list_1"}],
        [{"text": "🎲 Случайный рецепт", "callback_data": "random"}],
        [{"text": "❓ Помощь", "callback_data": "help"}]
    ]
    return {"inline_keyboard": keyboard}

def create_keyboard(recipes, page, per_page=5):
    total_pages = (len(recipes) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    page_recipes = recipes[start:end]
    
    keyboard = []
    for i, recipe in enumerate(page_recipes):
        actual_num = start + i + 1
        keyboard.append([{"text": f"{actual_num}. {recipe['name'][:30]}", "callback_data": f"recipe_{recipe['id']}"}])
    
    nav_row = []
    if page > 1:
        nav_row.append({"text": "◀ Назад", "callback_data": f"page_{page - 1}"})
    if page < total_pages:
        nav_row.append({"text": "Вперед ▶", "callback_data": f"page_{page + 1}"})
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([{"text": "🏠 Главное меню", "callback_data": "menu"}])
    return {"inline_keyboard": keyboard}

print("🚀 Бот запущен!")

if __name__ == "__main__":
    recipes_cache = []
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
                        
                        if time.time() - cache_time > 300 or not recipes_cache:
                            recipes_cache = get_recipes()
                            cache_time = time.time()
                        
                        callback_url = f"{BASE_URL}/answerCallbackQuery"
                        requests.post(callback_url, json={"callback_query_id": query["id"]})
                        
                        if data == "menu":
                            send_message(chat_id, "🍳 <b>Главное меню</b>\n\nВыберите действие:", create_menu_keyboard())
                        elif data == "help":
                            send_message(chat_id, "🍳 Помощь: /start - запуск, /recipes - рецепты, /random - случайный", create_menu_keyboard())
                        elif data == "random":
                            recipe = get_random_recipe()
                            if recipe:
                                photo = get_photo_url(recipe)
                                caption = format_recipe_full(recipe)
                                if photo:
                                    send_photo(chat_id, photo, caption)
                                else:
                                    send_message(chat_id, caption)
                            else:
                                send_message(chat_id, "❌ Не удалось найти рецепты")
                        elif data.startswith("list_"):
                            page = int(data.split("_")[1])
                            if recipes_cache:
                                send_message(chat_id, f"📖 <b>Список рецептов</b> — страница {page}", create_keyboard(recipes_cache, page))
                        elif data.startswith("recipe_"):
                            recipe_id = data.split("_")[1]
                            for r in recipes_cache:
                                if str(r.get("id")) == recipe_id:
                                    photo = get_photo_url(r)
                                    caption = format_recipe_full(r)
                                    if photo:
                                        send_photo(chat_id, photo, caption)
                                    else:
                                        send_message(chat_id, caption)
                                    break
                        elif data.startswith("page_"):
                            page = int(data.split("_")[1])
                            if recipes_cache:
                                send_message(chat_id, f"📖 <b>Список рецептов</b> — страница {page}", create_keyboard(recipes_cache, page))
                    
                    elif "message" in update:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"].get("text", "")
                        
                        if text == "/start":
                            send_message(chat_id, "🍳 <b>Добро пожаловать в DKana бот!</b>", create_menu_keyboard())
                        elif text == "/recipes":
                            recipes_cache = get_recipes()
                            cache_time = time.time()
                            if recipes_cache:
                                send_message(chat_id, f"📖 <b>Список рецептов</b> (всего {len(recipes_cache)})", create_keyboard(recipes_cache, 1))
                            else:
                                send_message(chat_id, "📭 Нет рецептов")
                        elif text == "/random":
                            recipe = get_random_recipe()
                            if recipe:
                                photo = get_photo_url(recipe)
                                caption = format_recipe_full(recipe)
                                if photo:
                                    send_photo(chat_id, photo, caption)
                                else:
                                    send_message(chat_id, caption)
                            else:
                                send_message(chat_id, "❌ Не удалось найти рецепты")
                        elif text == "/help":
                            send_message(chat_id, "🍳 Команды: /start, /recipes, /random")
                        else:
                            send_message(chat_id, "❓ Неизвестная команда. Используйте /help", create_menu_keyboard())
            
        except Exception as e:
            print(f"Ошибка: {e}")
        
        time.sleep(1)
