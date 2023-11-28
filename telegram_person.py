import asyncio
import os
from pyrogram import Client
from pyrogram import filters
from loguru import logger
from database import db
from models import User
from datetime import datetime
from pyrogram import StopPropagation


API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("my_account", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

logger.add("file.log", level="DEBUG")
# Переменная для отслеживания количества новых пользователей
new_users_count = 0


async def send_messages(user_id, message):
    await app.send_message(user_id, message)
    logger.info(f"Message sent to user {user_id} at {datetime.now()}: {message}")


async def check_trigger(user_id):
    chat_history = [msg.text async for msg in app.get_chat_history(user_id, limit=5)]
    return "Хорошего дня" not in chat_history


async def users_today_command(user_id):
    today_users = db.query(User).filter(User.registered_at >= datetime.today()).count()
    await app.send_message(user_id, f"Количество зарегистрированных пользователей за сегодня: {today_users}")


@app.on_message(filters.command("users_today") & filters.private)
async def users_today(client, message):
    user_id = message.from_user.id
    await users_today_command(user_id)


async def prepare_material(user_id):
    await asyncio.sleep(5400)  # Задержка в 90 минут (90 минут * 60 секунд)
    await send_messages(user_id, "Подготовила для вас материал")


async def send_initial_photo(user_id):
    photo_path = "mosyabot.jpg"
    # Отправляем фото пользователю
    await app.send_photo(user_id, photo=photo_path)
    logger.info(f"Initial photo sent to user {user_id}")


async def return_with_new_material(user_id):
    await send_messages(user_id, "Скоро вернусь с новым материалом!")


async def check_trigger_in_history(user_id):
    try:
        history = await app.get_chat_history(user_id, limit=10)
        messages = [message.text for message in history]
        print(f"Messages in history: {messages}")

        if any("хорошего дня" in message.lower() for message in messages):
            print("Trigger found!")
            return False  # Триггер найден

        # Триггер не найден
        return True
    except Exception as e:
        logger.error(f"Error checking trigger in history for user {user_id}: {str(e)}")
        return False


async def scheduled_check_and_return(user_id):
    while True:
        # Проверяем наличие триггера "Хорошего дня" в истории
        trigger_not_found = check_trigger_in_history(user_id)

        if trigger_not_found:
            # Если триггер не найден, отправляем сообщение
            await return_with_new_material(user_id)
            # Вызываем функцию users_today_command после отправки нового материала
            await users_today_command(user_id)

        # Ждем 2 часа перед каждой следующей проверкой
        await asyncio.sleep(7200)


@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user_id = message.from_user.id

    existing_user = db.query(User).filter(User.id == user_id).first()

    if not existing_user:
        new_user = User(id=user_id, username=message.from_user.username)
        db.add(new_user)

    # Задержка в 10 минут перед отправкой "Добрый день!"
    await asyncio.sleep(600)
    await send_messages(user_id, "Добрый день!")

    # Вызываем функцию подготовки материала с задержкой в 90 минут
    asyncio.ensure_future(prepare_material(user_id))

    # Отправляем фото пользователю, сразу после команды start
    await send_initial_photo(user_id)

    # Вызываем функцию асинхронной проверки и возврата каждые 2 часа
    asyncio.ensure_future(scheduled_check_and_return(user_id))

    raise StopPropagation


if __name__ == '__main__':
    app.run()
