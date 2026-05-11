import os
import requests
import time
import random

# Переменные окружения (задайте их в настройках бота)
BOT_TOKEN = "8703098869:AAGANurvwhEfO8gAFr0Q5l6Dbpi2Q-YdsDo"
DKANA_API_KEY = "5c6275a18b4bc810e9f2d70db41c4f51"  # замените на реальный ключ
DKANA_API_URL = "https://udkana.ru/api/v1"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
last_update_id = 0

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        print(f"Ошибка: {e}")

def get_recipes():
    url = f"{DKANA_API_URL}/recipes?limit=15&api_key={DKANA_API_KEY}"
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

def format_recipe(recipe):
    text = f"🍲 <b>{recipe['name']}</b>\n"
    text += f"📌 {recipe['type']}\n\n"
    text += "<b>Ингредиенты:</b>\n"
    for ing in recipe.get("ingredients", [])[:10]:
        text += f"• {ing['name']}: {ing['amount']} {ing['unit']}\n"
    return text

print("🚀 Бот запущен!")
while True:
    try:
        url = f"{BASE_URL}/getUpdates?offset={last_update_id + 1}&timeout=30"
        response = requests.get(url, timeout=35)
        
        if response.status_code == 200:
            updates = response.json().get("result", [])
            for update in updates:
                last_update_id = update["update_id"]
                chat_id = update["message"]["chat"]["id"]
                text = update["message"].get("text", "")
                
                if text == "/start":
                    send_message(chat_id, "🍳 Привет! Я бот DKana.\n\n/recipes - список рецептов\n/random - случайный рецепт")
                elif text == "/recipes":
                    recipes = get_recipes()
                    if recipes:
                        msg = "📖 Рецепты:\n\n"
                        for i, r in enumerate(recipes[:15]):
                            msg += f"{i+1}. {r['name']}\n"
                        send_message(chat_id, msg)
                    else:
                        send_message(chat_id, "📭 Нет рецептов")
                elif text == "/random":
                    recipe = get_random_recipe()
                    if recipe:
                        send_message(chat_id, format_recipe(recipe))
                    else:
                        send_message(chat_id, "❌ Не удалось найти рецепты")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    time.sleep(1)
