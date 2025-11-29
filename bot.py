import discord
from discord.ext import tasks, commands
import aiohttp
import logging
from logging.handlers import TimedRotatingFileHandler
from config import *

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # уровень логов (DEBUG, INFO, WARNING, ERROR)
    format="[{asctime}] [{levelname:^7}] {name}: {message}",
    style="{",
    handlers=[
        TimedRotatingFileHandler(
            "bot.log", when="midnight", interval=1, backupCount=0, encoding="utf-8"
        ),  # лог сбрасывается раз в сутки
        logging.StreamHandler()  # вывод в консоль
    ]
)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logging.info(f"Бот {bot.user} запущен!")
    update_player_count.start()

def format_count(number: int) -> str:
    """Форматирует число игроков (999, 1.2k, 1.2M)"""
    if number >= 1_000_000:
        return f"{number/1_000_000:.1f}M"
    elif number >= 1_000:
        return f"{number/1_000:.1f}k"
    else:
        return str(number)

async def set_channel_status(status_icon: str):
    """Устанавливает статус канала при ошибке или выключении"""
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        logging.error("Сервер не найден для смены статуса")
        return

    channel = guild.get_channel(VOICE_CHANNEL_ID)
    if not channel:
        logging.error("Канал не найден для смены статуса")
        return

    new_name = f"🌍hunt-игроков онлайн: {status_icon}"
    await channel.edit(name=new_name)
    logging.info(f"Статус канала изменён на {status_icon}")

@tasks.loop(seconds=UPDATE_INTERVAL_SECONDS)
async def update_player_count():
    """Запрашивает количество игроков в Hunt и обновляет название канала"""
    try:
        url = f"{STEAM_API_BASE_URL}?appid={STEAM_APP_ID}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logging.error(f"Ошибка Steam API: {response.status}")
                    return

                data = await response.json()
                current_count = data["response"]["player_count"]

                guild = bot.get_guild(GUILD_ID)
                if not guild:
                    logging.error("Сервер не найден")
                    return

                channel = guild.get_channel(VOICE_CHANNEL_ID)
                if not channel:
                    logging.error("Канал не найден")
                    return

                formatted_count = format_count(current_count)
                new_name = f"🌍hunt-игроков онлайн: {formatted_count}"
                await channel.edit(name=new_name)

                logging.info(f"Игроков онлайн: {current_count} → {formatted_count}")

    except Exception as e:
        logging.exception(f"Неожиданная ошибка: {e}")
        await set_channel_status("🟡")

original_close = bot.close

async def custom_close():
    logging.info("Бот закрывается → ставим статус ⚫")
    try:
        await set_channel_status("⚫")
    except Exception as e:
        logging.error(f"Не удалось сменить статус при закрытии: {e}")
    await original_close()

bot.close = custom_close

bot.run(TOKEN)