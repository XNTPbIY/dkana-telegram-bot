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

def send_message(chat_id, text, reply_markup=None):
    url = f"{BASE_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = reply_markup
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        print(f"Ошибка: {e}")

def get_feed(limit=50):
    url = f"{DKANA_API_URL}/feed?limit={limit}&api_key={DKANA_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json().get("feed", [])
    except:
        pass
    return []

def get_recipe_by_id(recipe_id):
    feed = get_feed(100)
    for item in feed:
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
    
    text = f"🍲 <b>{recipe.get('name', 'Без названия')}</b>\n"
    text += f"👤 Автор: {author}\n"
    text += f"❤️ Лайков: {item.get('likes', 0)}\n"
    text += f"📌 Тип: {recipe.get('type', 'Не указан')}\n\n"
    
    ings = recipe.get("ingredients", [])
    if ings:
        text += "<b>🛒 Ингредиенты:</b>\n"
        for ing in ings[:8]:
            text += f"• {ing['name']}: {ing['amount']} {ing['unit']}\n"
        if len(ings) > 8:
            text += "...\n"
    
    desc = recipe.get("description", "")
    if desc:
        text += f"\n<b>📖 Приготовление:</b>\n{desc[:300]}"
        if len(desc) > 300:
            text += "..."
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "🏠 Главное меню", "callback_data": "menu"}]
        ]
    }
    send_message(chat_id, text, keyboard)

print("🚀 Бот запущен!")

if __name__ == "__main__":
    feed_cache = []
    
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
                                    [{"text": "🎲 Случайный", "callback_data": "random"}]
                                ]
                            }
                            send_message(chat_id, "🍳 Главное меню", kb)
                        elif data == "random":
                            feed = get_feed(50)
                            if feed:
                                item = random.choice(feed)
                                show_recipe(chat_id, item.get("id"))
                            else:
                                send_message(chat_id, "📭 Лента пуста")
                        elif data.startswith("list_"):
                            feed_cache = get_feed(50)
                            if feed_cache:
                                kb = {"inline_keyboard": []}
                                for i, it in enumerate(feed_cache[:10]):
                                    name = it.get("recipe", {}).get("name", "Без названия")[:25]
                                    kb["inline_keyboard"].append([{"text": f"{i+1}. {name}", "callback_data": f"item_{it.get('id')}"}])
                                kb["inline_keyboard"].append([{"text": "🏠 Главное меню", "callback_data": "menu"}])
                                send_message(chat_id, f"📖 Лента ({len(feed_cache)} рец.)", kb)
                            else:
                                send_message(chat_id, "📭 Лента пуста")
                        elif data.startswith("item_"):
                            rid = data.split("_")[1]
                            show_recipe(chat_id, rid)
                    
                    elif "message" in update:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"].get("text", "")
                        chat_type = update["message"]["chat"].get("type", "")
                        
                        if chat_type == "channel":
                            continue
                        
                        kb = {
                            "inline_keyboard": [
                                [{"text": "📖 Лента", "callback_data": "list_1"}],
                                [{"text": "🎲 Случайный", "callback_data": "random"}]
                            ]
                        }
                        
                        if text == "/start":
                            send_message(chat_id, "🍳 Добро пожаловать в DKana бот!", kb)
                        elif text == "/feed":
                            feed_cache = get_feed(50)
                            if feed_cache:
                                kb2 = {"inline_keyboard": []}
                                for i, it in enumerate(feed_cache[:10]):
                                    name = it.get("recipe", {}).get("name", "Без названия")[:25]
                                    kb2["inline_keyboard"].append([{"text": f"{i+1}. {name}", "callback_data": f"item_{it.get('id')}"}])
                                kb2["inline_keyboard"].append([{"text": "🏠 Главное меню", "callback_data": "menu"}])
                                send_message(chat_id, f"📖 Лента ({len(feed_cache)} рец.)", kb2)
                            else:
                                send_message(chat_id, "📭 Лента пуста", kb)
                        elif text == "/random":
                            feed = get_feed(50)
                            if feed:
                                item = random.choice(feed)
                                show_recipe(chat_id, item.get("id"))
                            else:
                                send_message(chat_id, "📭 Лента пуста", kb)
                        elif text == "/help":
                            send_message(chat_id, "🍳 Команды:\n/start - меню\n/feed - лента\n/random - случайный рецепт", kb)
            
        except Exception as e:
            print(f"Ошибка: {e}")
        
        time.sleep(1)
