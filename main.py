import logging
from aiogram import Bot, Dispatcher, Router, F
import asyncio
from aiogram.filters import Command
from aiogram.types import Message
import aiosqlite

API_TOKEN = 'token'

# Настройка логирования
logging.basicConfig(level=logging.INFO)


# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
# Путь к базе данных SQLite
DB_FILE = 'shopping_list.db'


# Функция для удаления всех элементов из списка покупок пользователя
async def delete_all_items(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''DELETE FROM items WHERE user_id = ?''', (user_id,))
        await db.commit()



# Инициализация базы данных
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS items (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            name TEXT NOT NULL,
                            quantity TEXT NOT NULL,
                            times_added INTEGER NOT NULL DEFAULT 1
                        )''')
        await db.commit()


# Функция для добавления элемента в список покупок
async def add_item(user_id, name, quantity):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('''SELECT * FROM items WHERE user_id = ? AND name = ?''', (user_id, name)) as cursor:
            existing_item = await cursor.fetchone()
            if existing_item:
                await db.execute('''UPDATE items 
                                   SET quantity = quantity + ?, times_added = times_added + 1 
                                   WHERE user_id = ? AND name = ?''', (quantity, user_id, name))
            else:
                await db.execute('''INSERT INTO items (user_id, name, quantity) VALUES (?, ?, ?)''', (user_id, name, quantity))
            await db.commit()


# Функция для получения всех элементов списка покупок
async def get_items(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('''SELECT name, quantity FROM items WHERE user_id = ?''', (user_id,)) as cursor:
            items = await cursor.fetchall()
            return items


# Функция для удаления элемента из списка покупок
async def delete_item(user_id, name):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''DELETE FROM items WHERE user_id = ? AND name = ?''', (user_id, name))
        await db.commit()


# Обработчики команд бота
@dp.message(F.text, Command("start"))
async def send_welcome(message: Message):
    await message.reply("Привет! Я умный бот для списка покупок. Используй команды /add, /list и /delete.")


@dp.message(F.text, Command("add"))
async def add_command(message: Message):
    user_id = message.from_user.id
    try:
        args = message.text.split()
        del args[0]
        name = args[0]
        quantity = args[1]
        await add_item(user_id, name, quantity)
        await message.reply(f'Добавлено: {name}  -  {quantity}')
    except (IndexError, ValueError):
        await message.reply('Использование: /add <название> <количество>(поштучно или вес)')


@dp.message(F.text, Command("list"))
async def list_command(message: Message):
    user_id = message.from_user.id
    items = await get_items(user_id)
    if items:
        message_text = '\n'.join([f'{name}  -  {quantity}' for name, quantity in items])
        message_text = f"{message_text}\n\nДля очистки списка напишите комманду /paid"
    else:
        message_text = 'Ваш список покупок пуст'
    await message.reply(message_text)


@dp.message(F.text, Command("delete"))
async def delete_command(message: Message):
    user_id = message.from_user.id
    try:
        name = message.text.split()[1]
        await delete_item(user_id, name)
        await message.reply(f'{name} удален из списка покупок')
    except IndexError:
        await message.reply('Использование: /delete <название>')


@dp.message(F.text, Command("paid"))
async def paid_command(message: Message):
    user_id = message.from_user.id
    try:
        await delete_all_items(user_id)
        await message.reply('Список покупок очищен')
    except Exception as e:
        await message.reply(f'Произошла ошибка при очистке списка покупок: {e}')



@dp.message()
async def send_welcome(message: Message):
    await message.reply("Привет! Я умный бот для списка покупок. Используй команды /add, /list и /delete.")








# Запуск бота
async def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    router = Router()
    await init_db()
    dp.include_router(router)
    
    print('Бот включен')
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await dp.fsm.storage.close()
        await dp.fsm.storage.wait_closed()

if __name__ == '__main__':
    asyncio.run(main())

