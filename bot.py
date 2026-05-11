import os
import requests
import time
import random

# ===== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DKANA_API_KEY = os.environ.get("DKANA_API_KEY")
DKANA_API_URL = os.environ.get("DKANA_API_URL", "https://udkana.ru/api/v1")

if not BOT_TOKEN:
    raise Exception("❌ BOT_TOKEN не задан!")
if not DKANA_API_KEY:
    raise Exception("❌ DKANA_API_KEY не задан!")

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
    """Отправляет фото с подписью"""
    url = f"{BASE_URL}/sendPhoto"
    data = {"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        # Если фото не отправилось, отправляем текст
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

def get_recipe_by_id(recipes, recipe_id):
    for recipe in recipes:
        if str(recipe.get("id")) == str(recipe_id):
            return recipe
    return None

def format_recipe_short(recipe, index, total):
    """Краткий формат для списка"""
    return f"{index}. <b>{recipe['name']}</b>"

def format_recipe_full(recipe):
    """Полный формат рецепта"""
    text = f"🍲 <b>{recipe['name']}</b>\n"
    text += f"📌 <i>{recipe['type']}</i>\n\n"
    
    # Ингредиенты
    text += "<b>🛒 Ингредиенты:</b>\n"
    for ing in recipe.get("ingredients", [])[:15]:
        text += f"• {ing['name']}: {ing['amount']} {ing['unit']}\n"
    
    if len(recipe.get("ingredients", [])) > 15:
        text += f"... и ещё {len(recipe['ingredients']) - 15} ингредиентов\n"
    
    # Описание (первые 500 символов)
    if recipe.get("description"):
        desc = recipe['description'][:500]
        if len(recipe['description']) > 500:
            desc += "..."
        text += f"\n<b>📖 Приготовление:</b>\n{desc}\n"
    
    # Ссылка на сайт
    text += f"\n🔗 <a href='https://udkana.ru/'>В гостях у DKana</a>"
    
    return text

def get_photo_url(recipe):
    """Получает первую фотографию рецепта"""
    photos = recipe.get("photos", [])
    if photos:
        # Если фото в формате base64, не отправляем (слишком большие)
        first_photo = photos[0]
        if first_photo.startswith("http"):
            return first_photo
    return None

def create_keyboard(recipes, page, per_page=5):
    """Создаёт клавиатуру с кнопками рецептов"""
    total_pages = (len(recipes) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    page_recipes = recipes[start:end]
    
    keyboard = []
    
    # Кнопки с номерами рецептов
    for i, recipe in enumerate(page_recipes):
        actual_num = start + i + 1
        keyboard.append([{"text": f"{actual_num}. {recipe['name'][:30]}", "callback_data": f"recipe_{recipe['id']}"}])
    
    # Кнопки навигации
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
    """Главное меню"""
    keyboard = [
        [{"text": "📖 Список рецептов", "callback_data": "list_1"}],
        [{"text": "🎲 Случайный рецепт", "callback_data": "random"}],
        [{"text": "❓ Помощь", "callback_data": "help"}]
    ]
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
                    
                    # Обработка callback_query (нажатие на кнопку)
                    if "callback_query" in update:
                        query = update["callback_query"]
                        chat_id = query["message"]["chat"]["id"]
                        data = query["data"]
                        
                        # Обновляем кэш рецептов раз в 5 минут
                        if time.time() - cache_time > 300 or not recipes_cache:
                            recipes_cache = get_recipes()
                            cache_time = time.time()
                        
                        # Ответ на callback
                        callback_url = f"{BASE_URL}/answerCallbackQuery"
                        requests.post(callback_url, json={"callback_query_id": query["id"]})
                        
                        if data == "menu":
                            send_message(chat_id, "🍳 <b>Главное меню</b>\n\nВыберите действие:", create_menu_keyboard())
                        
                        elif data == "help":
                            help_text = "🍳 <b>Помощь по боту DKana</b>\n\n"
                            help_text += "/start - запустить бота\n"
                            help_text += "/recipes - список рецептов\n"
                            help_text += "/random - случайный рецепт\n\n"
                            help_text += "🔗 <a href='https://udkana.ru'>Перейти на сайт</a>"
                            send_message(chat_id, help_text)
                        
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
                            else:
                                send_message(chat_id, "📭 Нет рецептов")
                        
                        elif data.startswith("recipe_"):
                            recipe_id = data.split("_")[1]
                            recipe = get_recipe_by_id(recipes_cache, recipe_id)
                            if recipe:
                                photo = get_photo_url(recipe)
                                caption = format_recipe_full(recipe)
                                if photo:
                                    send_photo(chat_id, photo, caption)
                                else:
                                    send_message(chat_id, caption)
                            else:
                                send_message(chat_id, "❌ Рецепт не найден")
                        
                        elif data.startswith("page_"):
                            page = int(data.split("_")[1])
                            if recipes_cache:
                                send_message(chat_id, f"📖 <b>Список рецептов</b> — страница {page}", create_keyboard(recipes_cache, page))
                    
                    # Обработка обычных сообщений
                    elif "message" in update:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"].get("text", "")
                        
                        if text == "/start":
                            send_message(chat_id, "🍳 <b>Добро пожаловать в DKana бот!</b>\n\nЯ помогу вам следить за вашими рецептами.", create_menu_keyboard())
                        
                        elif text == "/recipes":
                            recipes_cache = get_recipes()
                            cache_time = time.time()
                            if recipes_cache:
                                send_message(chat_id, f"📖 <b>Список рецептов</b> (всего {len(recipes_cache)}) — страница 1", create_keyboard(recipes_cache, 1))
                            else:
                                send_message(chat_id, "📭 У вас пока нет рецептов в DKana")
                        
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
                            help_text = "🍳 <b>Помощь по боту DKana</b>\n\n"
                            help_text += "/start - запустить бота\n"
                            help_text += "/recipes - список рецептов\n"
                            help_text += "/random - случайный рецепт\n\n"
                            help_text += "🔗 <a href='https://udkana.ru'>Перейти на сайт</a>"
                            send_message(chat_id, help_text)
                        
                        else:
                            send_message(chat_id, "❓ Неизвестная команда. Используйте /help", create_menu_keyboard())
            
        except Exception as e:
            print(f"Ошибка: {e}")
        
        time.sleep(1)
