import pygame
import minecraft_launcher_lib
import subprocess
import os
import threading
import sys
import json
import psutil
import uuid
import socket
import traceback
import urllib3
import xml.etree.ElementTree as ET
import shutil
import re
import platform
import zipfile
from minecraft_launcher_lib.exceptions import InvalidChecksum
import random
import math
from tkinter import messagebox
from dotenv import load_dotenv
# Добавьте в начало файла после импортов:
import gc
gc.enable()
gc.set_threshold(700, 10, 5)  # Оптимизация сборщика мусора

load_dotenv()
import logging
from datetime import datetime

logger = None
LOG_FILE_PATH = None

def setup_logging():
    """Настраивает систему логирования в файл"""
    global logger, LOG_FILE_PATH

    # Определяем путь к лог-файлу
    # Пока используем временный путь, после инициализации GAME_DIR обновим
    if getattr(sys, 'frozen', False):
        temp_dir = os.path.dirname(sys.executable)
    else:
        temp_dir = os.path.dirname(os.path.abspath(__file__))

    LOG_FILE_PATH = os.path.join(temp_dir, "turbo_launcher.log")

    # Создаём логгер
    logger = logging.getLogger('TurboLauncher')
    logger.setLevel(logging.DEBUG)

    # Очищаем старые обработчики
    if logger.handlers:
        logger.handlers.clear()

    # Файловый обработчик
    file_handler = logging.FileHandler(LOG_FILE_PATH, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Консольный обработчик (для отладки)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    logger.info("=" * 60)
    logger.info(f"Turbo Launcher запущен")
    logger.info(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Лог-файл: {LOG_FILE_PATH}")
    logger.info("=" * 60)

    return logger

def update_log_path(game_dir):
    """Обновляет путь к лог-файлу после определения GAME_DIR"""
    global LOG_FILE_PATH, logger
    if logger and game_dir:
        new_log_path = os.path.join(game_dir, "turbo_launcher.log")
        if new_log_path != LOG_FILE_PATH:
            LOG_FILE_PATH = new_log_path
            # Перенастраиваем файловый обработчик
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    logger.removeHandler(handler)
            new_handler = logging.FileHandler(LOG_FILE_PATH, encoding='utf-8')
            new_handler.setLevel(logging.DEBUG)
            new_handler.setFormatter(
                logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
            logger.addHandler(new_handler)
            logger.info(f"Лог-файл перенесён в: {LOG_FILE_PATH}")

def open_log_file():
    """Открывает файл лога в стандартном просмотрщике"""
    global LOG_FILE_PATH
    try:
        if LOG_FILE_PATH and os.path.exists(LOG_FILE_PATH):
            if platform.system() == "Windows":
                os.startfile(LOG_FILE_PATH)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", LOG_FILE_PATH])
            else:  # Linux
                subprocess.run(["xdg-open", LOG_FILE_PATH])
            if logger:
                logger.info(f"Открыт файл лога: {LOG_FILE_PATH}")
        else:
            # Создаём лог-файл если его нет
            with open(LOG_FILE_PATH, 'w', encoding='utf-8') as f:
                f.write(f"Лог-файл Turbo Launcher\n")
                f.write(f"Создан: {datetime.now()}\n")
                f.write("=" * 50 + "\n")
            if platform.system() == "Windows":
                os.startfile(LOG_FILE_PATH)
    except Exception as e:
        if logger:
            logger.error(f"Не удалось открыть файл лога: {e}")

# Инициализируем временный логгер
setup_logging()
import sys
from contextlib import redirect_stdout, redirect_stderr

class TeeLogger:
    """Перенаправляет stdout и stderr одновременно в консоль и в лог-файл"""

    def __init__(self, log_file_path):
        self.terminal = sys.stdout
        self.log_file = None
        self.log_path = log_file_path

    def write(self, message):
        self.terminal.write(message)
        if self.log_file and not self.log_file.closed:
            try:
                self.log_file.write(message)
                self.log_file.flush()
            except:
                pass

    def flush(self):
        self.terminal.flush()
        if self.log_file and not self.log_file.closed:
            self.log_file.flush()

    def open_log(self):
        try:
            if self.log_file and not self.log_file.closed:
                self.log_file.close()
            self.log_file = open(self.log_path, 'a', encoding='utf-8')
        except:
            pass

# Глобальная переменная для перенаправления
tee = None

def setup_print_redirect(game_dir):
    """Настраивает перенаправление всех print в лог-файл"""
    global tee
    log_path = os.path.join(game_dir, "turbo_launcher.log")
    tee = TeeLogger(log_path)
    tee.open_log()
    sys.stdout = tee
    sys.stderr = tee
    print(f" Весь вывод перенаправлен в лог-файл: {log_path}")

# ЗАПУСК ОБНОВЛЕНИЯ (updater.exe) С ПРОВЕРКОЙ ВЕРСИИ

import subprocess
import sys
import os
import requests
import json

VERSION_FILE = "version.txt"
FILES_LIST_URL = "https://gitflic.ru/project/turboteam/turbolaunchersetup/blob/raw?file=files.json"

def check_for_update():
    """Проверяет, есть ли новая версия на сервере"""
    try:
        # Получаем текущую версию (локально)
        local_version = ""
        if os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, "r") as f:
                local_version = f.read().strip()
        else:
            # Если файла нет — значит первый запуск, не обновляем
            return False

        # Получаем версию с сервера
        resp = requests.get(FILES_LIST_URL, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            server_version = data.get("version", "")
            return server_version != local_version
    except:
        pass
    return False

def check_and_run_updater():
    """Запускает updater.exe только если есть обновление"""

    if not check_for_update():
        print("Версия актуальна, запуск лаунчера...")
        return

    if getattr(sys, 'frozen', False):
        current_dir = os.path.dirname(sys.executable)
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))

    updater_path = os.path.join(current_dir, "updater.exe")

    if os.path.exists(updater_path):
        print("Найдено обновление, запуск updater.exe...")
        subprocess.Popen([updater_path])
        sys.exit(0)

check_and_run_updater()

current_lang = "ru"
LANG_FILE = "lang.json"

def load_languages():
    global TEXTS
    try:
        with open(LANG_FILE, 'r', encoding='utf-8') as f:
            TEXTS = json.load(f)
        print(f"Загружены переводы: {', '.join(TEXTS.keys())}")
    except Exception as e:
        print(f"Ошибка загрузки переводов: {e}")
        TEXTS = {"ru": {}, "en": {}}

def t(key, **kwargs):
    """Получить перевод по ключу с подстановкой параметров"""
    text = TEXTS.get(current_lang, TEXTS.get("ru", {})).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except:
            return text
    return text

load_languages()

from pypresence import Presence
import time

DISCORD_APP_ID = os.getenv("DISCORD_APP_ID")

discord_rpc = None
discord_connected = False

def start_discord_presence():
    global discord_rpc, discord_connected
    try:
        discord_rpc = Presence(DISCORD_APP_ID)
        discord_rpc.connect()
        discord_connected = True
        print(" Discord RPC подключён")
        update_discord_presence("В лаунчере", "      ")
    except Exception as e:
        print(f" Discord ошибка: {e}")

def update_discord_presence(state, details, start_time=None):
    global discord_rpc, discord_connected
    if not discord_connected or discord_rpc is None:
        return
    try:
        activity = {
            "state": state,
            "details": details,
            "large_image": "turbo_logo",
            "large_text": "Turbo Launcher"
        }
        if start_time is None:
            activity["start"] = int(time.time())
        else:
            activity["start"] = start_time
        discord_rpc.update(**activity)
    except Exception as e:
        print(f"  Discord ошибка: {e}")

def stop_discord_presence():
    global discord_rpc, discord_connected
    if discord_rpc and discord_connected:
        try:
            discord_rpc.clear()
            discord_rpc.close()
        except:
            pass
        discord_connected = False

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

def update_online_count(username, is_online):
    """Обновляет количество игроков онлайн в JSONBin и отправляет в Discord"""

    def _update():
        try:
            # БЕРЁМ ЗНАЧЕНИЕ ИЗ АРГУМЕНТА username
            player_name = username

            # Защита от пустого имени
            if not player_name or player_name == "None":
                player_name = "Turbo_Player"
                print(f" Имя пользователя было пустым, заменено на {player_name}")

            headers = {
                "X-Master-Key": JSONBIN_API_KEY,
                "Content-Type": "application/json"
            }

            # Получаем текущие данные
            resp = requests.get(JSONBIN_URL, headers={"X-Master-Key": JSONBIN_API_KEY}, timeout=10)

            if resp.status_code == 200:
                data = resp.json().get("record", {"players": [], "count": 0})
                players = data.get("players", [])
                players_before = players.copy()

                if is_online:
                    if player_name not in players:
                        players.append(player_name)
                        print(f"    {player_name} добавлен в онлайн")
                    else:
                        print(f" {player_name} уже был в онлайне")
                else:
                    if player_name in players:
                        players.remove(player_name)
                        print(f" {player_name} удалён из онлайна")

                # Обновляем данные
                new_data = {
                    "players": players,
                    "count": len(players),
                    "last_update": time.time()
                }

                put_resp = requests.put(JSONBIN_URL, headers=headers, json=new_data, timeout=10)
                if put_resp.status_code == 200:
                    print(f" Онлайн обновлён: {len(players)} игроков")

                    # Отправляем в Discord
                    if is_online:
                        send_discord_online_count(len(players), player_name)
                    else:
                        send_discord_online_count(len(players))
                else:
                    print(f" Ошибка обновления JSONBin: {put_resp.status_code}")
        except Exception as e:
            print(f" Ошибка обновления онлайн: {e}")

    threading.Thread(target=_update, daemon=True).start()

def send_discord_online_count(count, joined_player=None):
    """Отправляет количество онлайн в Discord"""

    def _send():
        try:
            if joined_player:
                content = f"**Сейчас в игре: {count} игроков, зашел '{joined_player}'**"
            else:
                content = f"**Сейчас в игре: {count} игроков**"

            data = {
                "content": content,
                "username": "Turbo Launcher Stats",
                "avatar_url": "https://i.postimg.cc/TP0wZMDy/Turbo-Launcher-Preview.png"
            }
            requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=5)
            print(f"  Discord: {content}")
        except Exception as e:
            print(f" Ошибка отправки в Discord: {e}")

    threading.Thread(target=_send, daemon=True).start()

# ПЕРЕОПРЕДЕЛЯЕМ requests.get НА БЕЗОПАСНУЮ ВЕРСИЮ
original_get = requests.get

def safe_get(url, **kwargs):
    # Убираем verify если он есть (чтобы не было конфликта)
    kwargs.pop('verify', None)
    session = get_session(url)
    return session.get(url, **kwargs)

requests.get = safe_get
requests.post = lambda url, **kwargs: get_session(url).post(url, **kwargs)
requests.put = lambda url, **kwargs: get_session(url).put(url, **kwargs)
import certifi
import warnings
from urllib3.exceptions import InsecureRequestWarning

# Только для проблемных доменов отключаем проверку
PROBLEM_DOMAINS = ["gitflic.ru", "bangbang93.com", "bmclapi2.bangbang93.com"]

def get_session(url, timeout=30):
    """Создаёт сессию с правильной SSL проверкой"""
    session = requests.Session()
    session.timeout = timeout

    # Проверяем, проблемный ли домен
    is_problem = any(domain in url for domain in PROBLEM_DOMAINS)

    if is_problem:
        # Для кривых сертификатов - отключаем проверку (но только для них)
        session.verify = False
        # Подавляем варнинги только для этих запросов
        warnings.filterwarnings("ignore", category=InsecureRequestWarning)
    else:
        # Для всех нормальных сайтов - полная проверка
        session.verify = certifi.where()

    return session

# Устанавливаем таймаут для всех сокетов
socket.setdefaulttimeout(30)
def get_safe_game_dir():
    """
    Создаёт портативную папку .turbo_launcher в директории лаунчера.
    """
    try:
        # Определяем директорию запуска
        if getattr(sys, 'frozen', False):
            # Скомпилированный exe
            current_dir = os.path.dirname(sys.executable)
        else:
            # Режим разработки (скрипт)
            current_dir = os.path.dirname(os.path.abspath(__file__))

        # Портативная папка - рядом с лаунчером
        game_dir = os.path.join(current_dir, ".turbo_launcher")

        # Проверяем права на запись
        test_file = os.path.join(current_dir, ".write_test")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except:
            # Нет прав на запись в текущей папке
            print(f"Нет прав на запись в {current_dir}, использую папку пользователя")
            fallback_dir = os.path.join(os.path.expanduser("~"), ".turbo_launcher")
            os.makedirs(fallback_dir, exist_ok=True)
            return fallback_dir

        # Создаём папку
        os.makedirs(game_dir, exist_ok=True)

        # Создаём маркер портативности (опционально)
        portable_marker = os.path.join(game_dir, "portable.txt")
        if not os.path.exists(portable_marker):
            with open(portable_marker, 'w') as f:
                f.write("Turbo Launcher Portable Mode\n")
                f.write(f"Created: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

        print(f" Портативная папка: {game_dir}")

        update_log_path(game_dir)
        return game_dir

    except Exception as e:
        print(f" Ошибка при создании портативной папки: {e}")
        # Fallback - директория пользователя
        fallback_dir = os.path.join(os.path.expanduser("~"), ".turbo_launcher")
        os.makedirs(fallback_dir, exist_ok=True)
        print(f" Использую fallback: {fallback_dir}")
        return fallback_dir
GAME_DIR = get_safe_game_dir()
CONFIG_FILE = os.path.join(GAME_DIR, "launcher_config.json")
JAVA_DIR = os.path.join(GAME_DIR, "runtime")

os.makedirs(JAVA_DIR, exist_ok=True)

MIRRORS = [
    "https://launchermeta.mojang.com",
    "https://piston-meta.mojang.com",
    "https://bmclapi2.bangbang93.com"
]

BMCLAPI = "https://launchermeta.mojang.com"
for mirror in MIRRORS:
    try:
        test = requests.get(f"{mirror}/mc/game/version_manifest.json",
                            timeout=5,
                            headers={'User-Agent': 'Mozilla/5.0'})
        if test.status_code == 200:
            BMCLAPI = mirror
            print(f"    Рабочее зеркало: {BMCLAPI}")
            break
    except Exception as e:
        print(f"Зеркало {mirror} не отвечает: {e}")
        continue

os.environ["MCL_API_BASEURL"] = BMCLAPI

FABRIC_MIRRORS = [
    "https://bmclapi2.bangbang93.com",
    "https://meta.fabricmc.net",
    "https://meta2.fabricmc.net",
    "https://meta3.fabricmc.net",
]

import minecraft_launcher_lib.fabric
import minecraft_launcher_lib.forge

cancel_requested = False
minecraft_process = None
installer_process = None

LAST_FABRIC_VERSION_FILE = os.path.join(GAME_DIR, "last_fabric_version.txt")

MODS_DB = {
    "1.21.11": {
    "fabric-api": "0.141.3+1.21.11",  # ← или любую >= 0.140.0
    "sodium": "mc1.21.11-0.8.7-fabric",
    "iris": "1.10.7+1.21.11-fabric"
    },
    "1.21.10": {
        "fabric-api": "0.134.1+1.21.10",
        "sodium": "mc1.21.10-0.7.3-fabric",
        "iris": "1.9.7+1.21.10-fabric"
    },
    "1.21.9": {
        "fabric-api": "0.134.1+1.21.9",
        "sodium": "mc1.21.10-0.7.3-fabric",
        "iris": "1.9.7+1.21.10-fabric"
    },
    "1.21.8": {
        "fabric-api": "0.136.1+1.21.8",
        "sodium": "mc1.21.8-0.7.3-fabric",
        "iris": "1.9.6+1.21.8-fabric"
    },
    "1.21.6": {
        "fabric-api": "0.128.2+1.21.6",
        "sodium": "mc1.21.8-0.7.3-fabric",
        "iris": "1.9.6+1.21.8-fabric"
    },
    "1.21.5": {
        "fabric-api": "0.134.1+1.21.5",
        "sodium": "mc1.21.5-0.6.13-fabric",
        "iris": "1.8.11+1.21.5-fabric"
    },
    "1.21.4": {
        "fabric-api": "0.119.4+1.21.4",
        "sodium": "mc1.21.4-0.6.13-fabric",
        "iris": "1.8.8+1.21.4-fabric"
    },
    "1.21.3": {
        "fabric-api": "0.134.1+1.21.3",
        "sodium": "mc1.21.3-0.6.13-fabric",
        "iris": "1.8.11+1.21.3-fabric"
    },
    "1.21.2": {
        "fabric-api": "0.134.1+1.21.2",
        "sodium": "mc1.21.2-0.6.13-fabric",
        "iris": "1.8.11+1.21.2-fabric"
    },
    "1.21.1": {
        "fabric-api": "0.134.1+1.21.1",
        "sodium": "mc1.21.1-0.6.13-fabric",
        "iris": "1.8.12+1.21.1-fabric"
    },
    "1.21": {
        "fabric-api": "0.134.1+1.21",
        "sodium": "mc1.21-0.6.13-fabric",
        "iris": "1.8.12+1.21-fabric"
    },
    "1.20.6": {
        "fabric-api": "0.91.1+1.20.6",
        "sodium": "mc1.20.6-0.5.11-fabric",
        "iris": "1.7.2+1.20.6"
    },
    "1.20.5": {
        "fabric-api": "0.134.1+1.20.5",
        "sodium": "mc1.20.5-0.5.11-fabric",
        "iris": "1.8.11+1.20.5-fabric"
    },
    "1.20.4": {
        "fabric-api": "0.134.1+1.20.4",
        "sodium": "mc1.20.4-0.5.8-fabric",
        "iris": "1.8.11+1.20.4-fabric"
    },
    "1.20.3": {
        "fabric-api": "0.134.1+1.20.3",
        "sodium": "mc1.20.3-0.5.8-fabric",
        "iris": "1.8.11+1.20.3-fabric"
    },
    "1.20.2": {
        "fabric-api": "0.134.1+1.20.2",
        "sodium": "mc1.20.2-0.5.5-fabric",
        "iris": "1.8.11+1.20.2-fabric"
    },
    "1.20.1": {
        "fabric-api": "0.134.1+1.20.1",
        "sodium": "mc1.20.1-0.5.13-fabric",
        "iris": "1.8.11+1.20.1-fabric"
    },
    "1.20": {
        "fabric-api": "0.134.1+1.20",
        "sodium": "mc1.20-0.5.11-fabric",
        "iris": "1.8.11+1.20-fabric"
    },
    "1.19.4": {
        "fabric-api": "0.134.1+1.19.4",
        "sodium": "mc1.19.4-0.4.10-fabric",
        "iris": "1.5.2"
    },
    "1.19.3": {
        "fabric-api": "0.76.1+1.19.3",
        "sodium": "mc1.19.3-0.4.9-fabric",
        "iris": "1.5.2"
    },
    "1.19.2": {
        "fabric-api": "0.76.1+1.19.2",
        "sodium": "mc1.19.2-0.4.4-fabric",
        "iris": "1.5.2"
    },
    "1.19.1": {
        "fabric-api": "0.76.1+1.19.1",
        "sodium": "mc1.19.2-0.4.4-fabric",
        "iris": "1.5.2"
    },
    "1.19": {
        "fabric-api": "0.76.1+1.19",
        "sodium": "mc1.19-0.4.2-fabric",
        "iris": "1.5.2"
    },
    "1.18.2": {
        "fabric-api": "0.76.1+1.18.2",
        "sodium": "mc1.18.2-0.4.1-fabric",
        "iris": "1.5.2"
    },
    "1.18.1": {
        "fabric-api": "0.76.1+1.18.1",
        "sodium": "mc1.18.1-0.4.0-alpha6-fabric",
        "iris": "1.5.2"
    },
    "1.18": {
        "fabric-api": "0.76.1+1.18",
        "sodium": "mc1.18-0.4.0-alpha5-fabric",
        "iris": "1.5.2"
    },
    "1.17.1": {
        "fabric-api": "0.76.1+1.17.1",
        "sodium": "mc1.17.1-0.3.4-fabric",
        "iris": "1.5.2"
    },
    "1.17": {
        "fabric-api": "0.76.1+1.17",
        "sodium": "mc1.17.1-0.3.4-fabric",
        "iris": "1.5.2"
    },
    "1.16.5": {
        "fabric-api": "0.76.1+1.16.5",
        "sodium": "mc1.16.5-0.2.0-fabric",
        "iris": "1.5.2"
    }
}

def get_java_major_version(java_path="java"):
    try:
        result = subprocess.run([java_path, "-version"], capture_output=True, text=True, timeout=10)
        output = result.stderr + result.stdout
        match = re.search(r'version "?(1\.8|1\.8\.0|8|11|17|21|22|23|24|25)_?\d*', output)
        if match:
            ver_str = match.group(1)
            if ver_str.startswith("1.8"):
                return 8
            else:
                return int(ver_str)
        match = re.search(r'version (\d+)', output)
        if match:
            return int(match.group(1))
    except Exception as e:
        print(f"Ошибка определения версии Java: {e}")
    return None

def find_system_java(min_version=8, max_version=17):
    try:
        if shutil.which("java"):
            ver = get_java_major_version("java")
            if ver and min_version <= ver <= max_version:
                return "java"
    except:
        pass

    # Специальная проверка для Java 25
    if min_version == 25 and max_version == 25:
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home and os.path.exists(java_home):
            java_exe = os.path.join(java_home, "bin", "java.exe" if platform.system() == "Windows" else "java")
            if os.path.exists(java_exe):
                ver = get_java_major_version(java_exe)
                if ver == 25:
                    return java_exe

        # Проверка стандартных путей для Java 25 на Windows
        if platform.system() == "Windows":
            possible_paths = [
                "C:\\Program Files\\Microsoft\\jdk-25.*\\bin\\java.exe",
                "C:\\Program Files (x86)\\Microsoft\\jdk-25.*\\bin\\java.exe"
            ]
            import glob
            for pattern in possible_paths:
                matches = glob.glob(pattern)
                if matches:
                    return matches[0]

    if platform.system() == "Windows":
        possible_roots = [
            os.environ.get("JAVA_HOME", ""),
            "C:\\Program Files\\Java",
            "C:\\Program Files (x86)\\Java",
            "C:\\Program Files\\Microsoft\\jdk-25.*",
            os.path.expanduser("~")
        ]
        for root in possible_roots:
            if not root or not os.path.exists(root):
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                if "java.exe" in filenames and "bin" in dirpath:
                    java_path = os.path.join(dirpath, "java.exe")
                    ver = get_java_major_version(java_path)
                    if ver and min_version <= ver <= max_version:
                        return java_path
    return None

def download_java(version=8, set_status=None):
    global cancel_requested
    os.makedirs(JAVA_DIR, exist_ok=True)
    system = platform.system().lower()
    arch = platform.machine().lower()
    if "arm" in arch or "aarch64" in arch:
        arch = "aarch64"
    elif "64" in arch:
        arch = "x64"
    else:
        arch = "x86"
    java_folder = os.path.join(JAVA_DIR, f"java{version}")
    java_bin = os.path.join(java_folder, "bin", "java.exe" if system == "windows" else "java")
    if os.path.exists(java_bin):
        print(f"    Java {version} уже скачана в {java_folder}")
        return java_bin

    # Специальная обработка для Java 25 (нужна для Minecraft 26.1+)
    if version == 25:
        return download_microsoft_java(version, set_status)

    if version == 8:
        feature_version = 8
    elif version in [11, 17, 21]:
        feature_version = version
    else:
        feature_version = 17

    os_type = "windows" if system == "windows" else "linux" if system == "linux" else "mac"
    api_url = f"https://api.adoptium.net/v3/assets/latest/{feature_version}/hotspot"
    params = {
        "architecture": arch,
        "image_type": "jre",
        "os": os_type,
        "vendor": "eclipse"
    }
    try:
        if set_status:
            set_status(f"Получение информации о Java {version}...")
        resp = requests.get(api_url, params=params, timeout=30)
        if resp.status_code != 200:
            print(f" Ошибка получения данных Java: {resp.status_code}")
            return None
        data = resp.json()
        if not data:
            print(" Нет доступных сборок Java")
            return None
        binary = data[0]["binary"]
        download_url = binary["package"]["link"]
        print(f"  Скачивание Java {version} с {download_url}")
        temp_archive = os.path.join(JAVA_DIR, f"java{version}_temp.zip")
        if os.path.exists(temp_archive):
            os.remove(temp_archive)
        r = requests.get(download_url, stream=True, timeout=120)
        if r.status_code != 200:
            print(f" Ошибка скачивания Java: {r.status_code}")
            return None
        total_size = int(r.headers.get('content-length', 0))
        downloaded = 0
        with open(temp_archive, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if cancel_requested:
                    f.close()
                    os.remove(temp_archive)
                    return None
                f.write(chunk)
                downloaded += len(chunk)
                if set_status:
                    percent = downloaded / total_size * 100 if total_size else 0
                    set_status(f"Загрузка Java {version}: {percent:.1f}%")
        if set_status:
            set_status(f"Распаковка Java {version}...")
        with zipfile.ZipFile(temp_archive, 'r') as zip_ref:
            top_level = None
            for name in zip_ref.namelist():
                if '/' in name:
                    top_level = name.split('/')[0]
                    break
            if top_level:
                extract_path = os.path.join(JAVA_DIR, "temp_extract")
                if os.path.exists(extract_path):
                    shutil.rmtree(extract_path)
                zip_ref.extractall(extract_path)
                if os.path.exists(java_folder):
                    shutil.rmtree(java_folder)
                shutil.move(os.path.join(extract_path, top_level), java_folder)
                shutil.rmtree(extract_path)
            else:
                zip_ref.extractall(java_folder)
        os.remove(temp_archive)
        print(f"    Java {version} установлена в {java_folder}")
        return java_bin
    except Exception as e:
        print(f" Ошибка при скачивании Java: {e}")
        traceback.print_exc()
        return None

def download_microsoft_java(version=25, set_status=None):
    """Скачивает Microsoft OpenJDK для Java 25 (нужна для Minecraft 26.1+)"""
    global cancel_requested
    system = platform.system().lower()
    arch = platform.machine().lower()

    if "arm" in arch or "aarch64" in arch:
        arch = "aarch64"
    elif "64" in arch:
        arch = "x64"
    else:
        arch = "x86"

    java_folder = os.path.join(JAVA_DIR, f"java{version}")
    java_bin = os.path.join(java_folder, "bin", "java.exe" if system == "windows" else "java")

    if os.path.exists(java_bin):
        print(f"    Java {version} уже скачана в {java_folder}")
        return java_bin

    # URL для Microsoft OpenJDK 25
    if system == "windows":
        if arch == "x64":
            download_url = "https://aka.ms/download-jdk/microsoft-jdk-25.0.2-windows-x64.zip"
        elif arch == "aarch64":
            download_url = "https://aka.ms/download-jdk/microsoft-jdk-25.0.2-windows-aarch64.zip"
        else:
            download_url = "https://aka.ms/download-jdk/microsoft-jdk-25.0.2-windows-x64.zip"
        file_ext = ".zip"
    elif system == "linux":
        if arch == "x64":
            download_url = "https://aka.ms/download-jdk/microsoft-jdk-25.0.2-linux-x64.tar.gz"
        elif arch == "aarch64":
            download_url = "https://aka.ms/download-jdk/microsoft-jdk-25.0.2-linux-aarch64.tar.gz"
        else:
            download_url = "https://aka.ms/download-jdk/microsoft-jdk-25.0.2-linux-x64.tar.gz"
        file_ext = ".tar.gz"
    elif system == "mac":
        if arch == "aarch64":
            download_url = "https://aka.ms/download-jdk/microsoft-jdk-25.0.2-mac-aarch64.tar.gz"
        else:
            download_url = "https://aka.ms/download-jdk/microsoft-jdk-25.0.2-mac-x64.tar.gz"
        file_ext = ".tar.gz"
    else:
        print(f" Неподдерживаемая ОС: {system}")
        return None

    try:
        if set_status:
            set_status(f"Скачивание Microsoft Java {version}...")

        temp_archive = os.path.join(JAVA_DIR, f"java{version}_temp{file_ext}")
        if os.path.exists(temp_archive):
            os.remove(temp_archive)

        print(f"  Скачивание Java {version} с {download_url}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(download_url, stream=True, timeout=180, headers=headers)

        if r.status_code != 200:
            print(f" Ошибка скачивания Java: {r.status_code}")
            return None

        total_size = int(r.headers.get('content-length', 0))
        downloaded = 0
        with open(temp_archive, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if cancel_requested:
                    f.close()
                    os.remove(temp_archive)
                    return None
                f.write(chunk)
                downloaded += len(chunk)
                if set_status:
                    percent = downloaded / total_size * 100 if total_size else 0
                    set_status(f"Загрузка Java {version}: {percent:.1f}%")

        if set_status:
            set_status(f"Распаковка Java {version}...")

        # Распаковка в зависимости от типа файла
        if file_ext == '.zip':
            with zipfile.ZipFile(temp_archive, 'r') as zip_ref:
                # Находим корневую папку
                top_level = None
                for name in zip_ref.namelist():
                    if '/' in name:
                        top_level = name.split('/')[0]
                        break

                extract_path = os.path.join(JAVA_DIR, "temp_extract")
                if os.path.exists(extract_path):
                    shutil.rmtree(extract_path)
                zip_ref.extractall(extract_path)

                if top_level:
                    source_dir = os.path.join(extract_path, top_level)
                    if os.path.exists(java_folder):
                        shutil.rmtree(java_folder)
                    shutil.move(source_dir, java_folder)
                    shutil.rmtree(extract_path)
                else:
                    if os.path.exists(java_folder):
                        shutil.rmtree(java_folder)
                    shutil.move(extract_path, java_folder)
        else:
            # .tar.gz
            import tarfile
            with tarfile.open(temp_archive, 'r:gz') as tar:
                # Находим корневую папку
                top_level = None
                for member in tar.getmembers():
                    if '/' in member.name:
                        top_level = member.name.split('/')[0]
                        break

                extract_path = os.path.join(JAVA_DIR, "temp_extract")
                if os.path.exists(extract_path):
                    shutil.rmtree(extract_path)
                tar.extractall(extract_path)

                if top_level:
                    source_dir = os.path.join(extract_path, top_level)
                    if os.path.exists(java_folder):
                        shutil.rmtree(java_folder)
                    shutil.move(source_dir, java_folder)
                    shutil.rmtree(extract_path)
                else:
                    if os.path.exists(java_folder):
                        shutil.rmtree(java_folder)
                    shutil.move(extract_path, java_folder)

        # Очистка
        if os.path.exists(temp_archive):
            os.remove(temp_archive)

        # Проверяем, что java бинарник существует
        if os.path.exists(java_bin):
            print(f"    Java {version} установлена в {java_folder}")
            return java_bin
        else:
            print(f" Не найден java бинарник после распаковки: {java_bin}")
            return None

    except Exception as e:
        print(f" Ошибка при скачивании Microsoft Java: {e}")
        traceback.print_exc()
        return None

def get_java_executable(minecraft_version, set_status=None):
    try:
        # Разбираем версию
        if minecraft_version.startswith('1.'):
            # Старый формат: 1.21.1, 1.20.4 и т.д.
            parts = minecraft_version.split('.')
            if len(parts) >= 2:
                minor = int(parts[1])
                if minor < 17:
                    required_java = 8      # 1.16 и ниже
                elif minor < 21:
                    required_java = 17     # 1.17 - 1.20
                else:
                    required_java = 21     # 1.21+
            else:
                required_java = 17
        else:
            # Новый формат: 26.1, 27.2 и т.д. (это 1.26.1, 1.27.2)
            try:
                # Парсим номер версии (26.1 -> 26)
                major_version = int(minecraft_version.split('.')[0])
                if major_version >= 26:
                    required_java = 25     # Minecraft 26+ требует Java 25
                elif major_version >= 24:
                    required_java = 21     # Minecraft 24+ требует Java 21
                else:
                    required_java = 21     # Fallback
            except:
                required_java = 25         # Если не смогли распарсить, берём Java 25
    except:
        required_java = 8

    print(f"  Для Minecraft {minecraft_version} требуется Java {required_java}")
    local_java = os.path.join(JAVA_DIR, f"java{required_java}", "bin", "java.exe" if platform.system() == "Windows" else "java")
    if os.path.exists(local_java):
        print(f"    Найдена локальная Java {required_java} в {local_java}")
        return local_java
    sys_java = find_system_java(min_version=required_java, max_version=required_java)
    if sys_java:
        print(f"    Найдена системная Java {required_java} по пути {sys_java}")
        return sys_java
    print(f" Java {required_java} не найдена, начинаем скачивание...")
    if set_status:
        set_status(f"Скачивание Java {required_java}...")
    downloaded = download_java(required_java, set_status)
    if downloaded:
        return downloaded
    else:
        print(" Не удалось скачать Java, пробуем системную java (может не подойти)")
        return "java"
def clear_mods_folder():
    mods_dir = os.path.join(GAME_DIR, "mods")
    if not os.path.exists(mods_dir):
        return
    for file in os.listdir(mods_dir):
        if file.endswith(".jar"):
            file_path = os.path.join(mods_dir, file)
            for attempt in range(3):
                try:
                    os.remove(file_path)
                    print(f"  Удалён мод: {file}")
                    break
                except Exception as e:
                    if attempt == 2:
                        print(f" Не удалось удалить {file}: {e}")
                    else:
                        time.sleep(0.5)

def get_last_fabric_version():
    if os.path.exists(LAST_FABRIC_VERSION_FILE):
        with open(LAST_FABRIC_VERSION_FILE, 'r') as f:
            return f.read().strip()
    return None

def set_last_fabric_version(version):
    with open(LAST_FABRIC_VERSION_FILE, 'w') as f:
        f.write(version)

def download_mod(mod_name: str, minecraft_version: str, game_dir: str, set_status) -> bool:
    """
    Скачивает мод с Modrinth.
    Приоритет:
      1. Точная версия из статической базы MODS_DB.
      2. Fallback на прямые ссылки для известных версий.
      3. Динамический поиск с пагинацией.
    """
    try:
        mod_ids = {
            "sodium": "AANobbMI",
            "iris": "YL57xq9U",
            "fabric-api": "P7dR8mSH"
        }

        if mod_name not in mod_ids:
            print(f" Неизвестный мод: {mod_name}")
            return False

        mod_id = mod_ids[mod_name]
        mods_dir = os.path.join(game_dir, "mods")
        os.makedirs(mods_dir, exist_ok=True)

        # ===== 1. Пытаемся взять версию из статической базы =====
        target_version = None
        if minecraft_version in MODS_DB and mod_name in MODS_DB[minecraft_version]:
            target_version = MODS_DB[minecraft_version][mod_name]
            print(f"  Статическая база: для {mod_name} указана версия {target_version}")

        # Функция для получения всех версий (пагинация)
        def fetch_all_versions():
            all_versions = []
            offset = 0
            limit = 100
            while True:
                params = {
                    "loaders": json.dumps(["fabric"]),
                    "limit": limit,
                    "offset": offset
                }
                try:
                    resp = requests.get(f"https://api.modrinth.com/v2/project/{mod_id}/version",
                                        params=params, timeout=15)
                    if resp.status_code != 200:
                        print(f"  Ошибка {resp.status_code} при offset={offset}")
                        break
                    data = resp.json()
                    if not data:
                        break
                    all_versions.extend(data)
                    if len(data) < limit:
                        break
                    offset += limit
                except Exception as e:
                    print(f"  Ошибка при запросе: {e}")
                    break
            return all_versions

        # Функция для проверки, подходит ли файл (сначала loaders, потом имя)
        def is_fabric_file(file):
            if "loaders" in file and "fabric" in file["loaders"]:
                return True
            if "fabric" in file["filename"].lower():
                return True
            return False

        # Функция для выбора лучшего файла из версии
        def select_best_file(version):
            for f in version["files"]:
                if "loaders" in f and "fabric" in f["loaders"]:
                    return f
            for f in version["files"]:
                if "fabric" in f["filename"].lower():
                    return f
            return version["files"][0]

        # ==== Попытка скачать по статической базе ====
        if target_version:
            all_versions = fetch_all_versions()
            exact_version = None
            for v in all_versions:
                if v.get("version_number") == target_version:
                    exact_version = v
                    break
            if exact_version:
                best_file = select_best_file(exact_version)
                if best_file:
                    print(f"    Найдена точная версия {target_version} из базы")
                    download_url = best_file["url"]
                    filename = best_file["filename"]
                    mod_path = os.path.join(mods_dir, filename)
                    if os.path.exists(mod_path):
                        print(f"    {mod_name} уже установлен (версия {filename})")
                        return True
                    set_status(f"Скачивание {mod_name}...")
                    print(f"  Скачивание {mod_name} (версия {filename}): {download_url}")
                    r = requests.get(download_url, stream=True, timeout=60)
                    if r.status_code == 200:
                        with open(mod_path, 'wb') as f:
                            for chunk in r.iter_content(8192):
                                if cancel_requested:
                                    f.close()
                                    os.remove(mod_path)
                                    return False
                                f.write(chunk)
                        print(f"    {mod_name} сохранён: {mod_path}")
                        return True
                    else:
                        print(f" Ошибка скачивания, код {r.status_code}")
                else:
                    print(f" Точная версия {target_version} не имеет подходящего файла")
            else:
                print(f" Точная версия {target_version} не найдена в API")

        # ===== 2. Fallback на прямые ссылки для известных версий =====
        fallback_sodium = {
            "1.21.4": "https://cdn.modrinth.com/data/AANobbMI/versions/c3YkZvne/sodium-fabric-0.6.13%2Bmc1.21.4.jar",
            "1.21.5": "https://cdn.modrinth.com/data/AANobbMI/versions/DA250htH/sodium-fabric-0.6.13%2Bmc1.21.5.jar",
            "1.21.6": "https://cdn.modrinth.com/data/AANobbMI/versions/7pwil2dy/sodium-fabric-0.7.3%2Bmc1.21.8.jar",
            "1.21.8": "https://cdn.modrinth.com/data/AANobbMI/versions/7pwil2dy/sodium-fabric-0.7.3%2Bmc1.21.8.jar",
            "1.21.9": "https://cdn.modrinth.com/data/AANobbMI/versions/AQpu5aS1/sodium-fabric-0.7.3%2Bmc1.21.9.jar",
            "1.21.10": "https://cdn.modrinth.com/data/AANobbMI/versions/sFfidWgd/sodium-fabric-0.7.3%2Bmc1.21.10.jar",
            "1.21.11": "https://cdn.modrinth.com/data/AANobbMI/versions/ZPWbiWXz/sodium-fabric-0.8.6%2Bmc1.21.11.jar",
        }

        fallback_iris = {
            "1.21.4": "https://cdn.modrinth.com/data/YL57xq9U/versions/Ca054sTe/iris-fabric-1.8.8%2Bmc1.21.4.jar",
            "1.21.5": "https://cdn.modrinth.com/data/YL57xq9U/versions/U6evbjd0/iris-fabric-1.8.11%2Bmc1.21.5.jar",
            "1.21.6": "https://cdn.modrinth.com/data/YL57xq9U/versions/Rhzf61g1/iris-fabric-1.9.6%2Bmc1.21.8.jar",
            "1.21.8": "https://cdn.modrinth.com/data/YL57xq9U/versions/Rhzf61g1/iris-fabric-1.9.6%2Bmc1.21.8.jar",
            "1.21.9": "https://cdn.modrinth.com/data/YL57xq9U/versions/2fEZLvCV/iris-fabric-1.9.7%2Bmc1.21.9.jar",
            "1.21.10": "https://cdn.modrinth.com/data/YL57xq9U/versions/a98UkgML/iris-fabric-1.9.7%2Bmc1.21.10.jar",
            "1.21.11": "https://cdn.modrinth.com/data/YL57xq9U/versions/TSXvi2yD/iris-fabric-1.10.6%2Bmc1.21.11.jar",
        }

        fallback_fabric_api = {
            # при необходимости можно добавить
        }

        fallback_map = {
            "sodium": fallback_sodium,
            "iris": fallback_iris,
            "fabric-api": fallback_fabric_api
        }

        if mod_name in fallback_map and minecraft_version in fallback_map[mod_name]:
            url = fallback_map[mod_name][minecraft_version]
            filename = os.path.basename(url)
            mod_path = os.path.join(mods_dir, filename)
            if os.path.exists(mod_path):
                print(f"    {mod_name} уже установлен (fallback)")
                return True
            set_status(f"Скачивание {mod_name} (fallback)...")
            try:
                r = requests.get(url, stream=True, timeout=60)
                if r.status_code == 200:
                    with open(mod_path, 'wb') as f:
                        for chunk in r.iter_content(8192):
                            if cancel_requested:
                                f.close()
                                os.remove(mod_path)
                                return False
                            f.write(chunk)
                    print(f"    {mod_name} сохранён (fallback): {mod_path}")
                    return True
                else:
                    print(f" Ошибка скачивания fallback, код {r.status_code}")
            except Exception as e:
                print(f" Ошибка при fallback: {e}")

        # ===== 3. Динамический поиск =====
        print(f"  Динамический поиск для {mod_name}...")
        all_versions = fetch_all_versions()
        if not all_versions:
            print(f" Не удалось получить версии {mod_name}")
            return False

        all_versions.sort(key=lambda v: v.get("date_published", ""), reverse=True)
        compatible = [v for v in all_versions if minecraft_version in v.get("game_versions", [])]
        print(f"  Найдено {len(compatible)} версий, совместимых с Minecraft {minecraft_version}")

        if not compatible:
            print(f" Нет версий {mod_name} для Minecraft {minecraft_version}")
            return False

        selected_version = None
        for v in compatible:
            for f in v["files"]:
                if is_fabric_file(f):
                    selected_version = v
                    break
            if selected_version:
                break
        if not selected_version:
            selected_version = compatible[0]
            print(f" ВНИМАНИЕ: ни одна версия не содержит очевидно Fabric-файл, выбрана {selected_version['version_number']}")

        best_file = select_best_file(selected_version)
        download_url = best_file["url"]
        filename = best_file["filename"]
        mod_path = os.path.join(mods_dir, filename)

        if os.path.exists(mod_path):
            print(f"    {mod_name} уже установлен (версия {filename})")
            return True

        set_status(f"Скачивание {mod_name}...")
        print(f"  Скачивание {mod_name} (версия {filename}): {download_url}")
        for attempt in range(3):
            try:
                r = requests.get(download_url, stream=True, timeout=60)
                if r.status_code == 200:
                    break
                else:
                    print(f"  Попытка {attempt+1}: код {r.status_code}")
            except Exception as e:
                print(f"Ошибка скачивания: {e}")
                if attempt < 2:
                    time.sleep(2)
                else:
                    return False
        else:
            return False

        with open(mod_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if cancel_requested:
                    f.close()
                    os.remove(mod_path)
                    return False
                f.write(chunk)

        print(f"    {mod_name} сохранён: {mod_path}")
        return True

    except Exception as e:
        print(f" Ошибка скачивания {mod_name}: {e}")
        traceback.print_exc()
        return False

def install_fabric_mods(minecraft_version: str, game_dir: str, set_status) -> bool:
    """
    Устанавливает моды динамически для любой версии Minecraft (1.16.5+)
    Автоматически ищет и скачивает совместимые версии с Modrinth
    """
    # Проверяем, поддерживает ли версия моды (только Fabric 1.16.5+)
    try:
        if minecraft_version.startswith('1.'):
            parts = minecraft_version.split('.')
            minor = int(parts[1])
            if minor < 16:
                set_status(f"Моды не поддерживаются для {minecraft_version} (нужна 1.16.5+)")
                print(f"  Пропускаем установку модов для {minecraft_version}")
                return True
            elif minor == 16:
                patch = int(parts[2]) if len(parts) > 2 else 0
                if patch < 5:
                    set_status(f"Моды могут не работать на {minecraft_version} (рекомендуется 1.16.5+)")
                    print(f"  Версия {minecraft_version} имеет ограниченную поддержку")
    except:
        pass

    mods_dir = os.path.join(game_dir, "mods")
    os.makedirs(mods_dir, exist_ok=True)
    results = {}

    # ID модов на Modrinth
    MODS_INFO = {
        "fabric-api": {"id": "P7dR8mSH", "required": True},
        "sodium": {"id": "AANobbMI", "required": False},
        "iris": {"id": "YL57xq9U", "required": False}
    }

    # Флаг - был ли использован MODS_DB для хотя бы одного мода
    used_static_db = False

    # ===== 1. СНАЧАЛА ПРОБУЕМ ВЗЯТЬ ВЕРСИИ ИЗ СТАТИЧЕСКОЙ БАЗЫ MODS_DB =====
    if minecraft_version in MODS_DB:
        used_static_db = True
        print(f"  Используем статическую базу MODS_DB для версии {minecraft_version}")

        for mod_name, mod_info in MODS_INFO.items():
            mod_id = mod_info["id"]
            required = mod_info["required"]

            if mod_name not in MODS_DB[minecraft_version]:
                if required:
                    set_status(f"Критическая ошибка: {mod_name} не найден в MODS_DB для {minecraft_version}!")
                    print(f"  {mod_name} отсутствует в статической базе")
                    return False
                else:
                    print(f"  {mod_name} пропущен (нет в статической базе)")
                    results[mod_name] = False
                    continue

            target_version = MODS_DB[minecraft_version][mod_name]
            print(f"  Статическая база: {mod_name} -> {target_version}")

            # Скачиваем по точной версии через download_mod
            success = download_mod(mod_name, minecraft_version, game_dir, set_status)
            results[mod_name] = success

            if not success and required:
                set_status(f"Ошибка: не удалось скачать {mod_name} {target_version}!")
                return False
    else:
        print(f"  Версия {minecraft_version} не найдена в MODS_DB, переходим к динамическому поиску")

    # ===== 2. ЕСЛИ ВЕРСИИ НЕТ В MODS_DB — ДИНАМИЧЕСКИЙ ПОИСК =====
    if not used_static_db:
        print(f"  Запускаем динамический поиск модов для {minecraft_version}")

        def fetch_mod_versions(mod_id):
            """Получает все версии мода с Modrinth"""
            all_versions = []
            offset = 0
            limit = 100

            while True:
                try:
                    params = {
                        "loaders": json.dumps(["fabric"]),
                        "limit": limit,
                        "offset": offset
                    }
                    resp = requests.get(f"https://api.modrinth.com/v2/project/{mod_id}/version",
                                        params=params, timeout=15)
                    if resp.status_code != 200:
                        break
                    data = resp.json()
                    if not data:
                        break
                    all_versions.extend(data)
                    if len(data) < limit:
                        break
                    offset += limit
                except Exception as e:
                    print(f"  Ошибка получения версий: {e}")
                    break
            return all_versions

        def is_version_compatible(version, mc_version):
            """Проверяет, совместима ли версия мода с Minecraft"""
            game_versions = version.get("game_versions", [])

            # Прямое совпадение
            if mc_version in game_versions:
                return True

            # Для версий 26.x (1.26.x)
            if mc_version.startswith("26."):
                alt_version = f"1.{mc_version}"
                if alt_version in game_versions:
                    return True

            # Совпадение по мажорной версии (например, все 1.21.x)
            if '.' in mc_version:
                major_minor = '.'.join(mc_version.split('.')[:2])
                for gv in game_versions:
                    if gv.startswith(major_minor):
                        return True

            return False

        def is_fabric_file(file_data):
            """Проверяет, подходит ли файл для Fabric"""
            if "loaders" in file_data and "fabric" in file_data["loaders"]:
                return True
            if "fabric" in file_data["filename"].lower():
                return True
            return False

        def download_mod_dynamic(mod_name, mod_id, mc_version):
            """Скачивает подходящую версию мода динамически"""
            print(f"  Поиск {mod_name} для Minecraft {mc_version}...")

            # Получаем все версии
            all_versions = fetch_mod_versions(mod_id)
            if not all_versions:
                print(f"  Не удалось получить версии {mod_name}")
                return False

            # Сортируем по дате (новые сначала)
            all_versions.sort(key=lambda v: v.get("date_published", ""), reverse=True)

            # Ищем совместимые версии
            compatible = []
            for version in all_versions:
                if is_version_compatible(version, mc_version):
                    compatible.append(version)

            print(f"  Найдено {len(compatible)} совместимых версий")

            if not compatible:
                return False

            # Выбираем стабильную версию (не alpha/beta)
            selected = None
            for version in compatible:
                ver_str = version.get("version_number", "").lower()
                if "alpha" not in ver_str and "beta" not in ver_str:
                    selected = version
                    break

            if not selected:
                selected = compatible[0]
                print(f"  Внимание: выбрана нестабильная версия {selected['version_number']}")
            else:
                print(f"  Выбрана версия {selected['version_number']}")

            # Выбираем подходящий файл
            selected_file = None
            for f in selected["files"]:
                if is_fabric_file(f):
                    selected_file = f
                    break

            if not selected_file:
                selected_file = selected["files"][0]

            download_url = selected_file["url"]
            filename = selected_file["filename"]
            mod_path = os.path.join(mods_dir, filename)

            # Проверяем, не установлен ли уже
            if os.path.exists(mod_path):
                print(f"  {mod_name} уже установлен ({filename})")
                return True

            # Скачиваем
            set_status(f"Скачивание {mod_name}...")
            print(f"  Скачивание: {filename}")

            for attempt in range(3):
                try:
                    r = requests.get(download_url, stream=True, timeout=60)
                    if r.status_code == 200:
                        with open(mod_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if cancel_requested:
                                    f.close()
                                    if os.path.exists(mod_path):
                                        os.remove(mod_path)
                                    return False
                                f.write(chunk)
                        file_size = os.path.getsize(mod_path)
                        print(f"  {mod_name} сохранён ({file_size} байт)")
                        return True
                    else:
                        print(f"  Попытка {attempt + 1}: код {r.status_code}")
                except Exception as e:
                    print(f"  Попытка {attempt + 1}: ошибка: {e}")
                    if attempt < 2:
                        time.sleep(2)
            return False

        # === УСТАНОВКА МОДОВ ДИНАМИЧЕСКИ ===
        set_status("Поиск и установка модов...")

        for mod_name, mod_info in MODS_INFO.items():
            mod_id = mod_info["id"]
            required = mod_info["required"]

            success = download_mod_dynamic(mod_name, mod_id, minecraft_version)
            results[mod_name] = success

            if not success and required:
                set_status(f"Критическая ошибка: {mod_name} не установлен!")
                print(f"  {mod_name} обязателен, но не установлен")
                return False

            if success:
                print(f"  {mod_name}  установлен")
            else:
                print(f"  {mod_name}  пропущен")

    # === ПРОВЕРКА СОВМЕСТИМОСТИ SODIUM И IRIS ===
    sodium_ok = results.get("sodium", False)
    iris_ok = results.get("iris", False)

    if not sodium_ok and iris_ok:
        set_status("Удаление Iris (требуется Sodium)...")
        for f in os.listdir(mods_dir):
            if f.startswith("iris-"):
                try:
                    os.remove(os.path.join(mods_dir, f))
                    print(f"  Удалён Iris: {f}")
                except:
                    pass
        results["iris"] = False

    # === ИТОГ ===
    installed_mods = [name for name, installed in results.items() if installed]

    if installed_mods:
        set_status(f"Моды установлены: {', '.join(installed_mods)}")
        print(f"\n  Установлено модов: {len(installed_mods)}/{len(MODS_INFO)}")
        print(f"  Список: {', '.join(installed_mods)}")
    else:
        set_status("Моды не установлены (нет совместимых версий)")
        print("  Не установлено ни одного мода")

    return results.get("fabric-api", False)
def fetch_fabric_data(endpoint: str, set_status, is_meta: bool = True):
    global cancel_requested
    for mirror in FABRIC_MIRRORS:
        if cancel_requested:
            return None
        base = mirror.rstrip('/')
        urls_to_try = [
            f"{base}/{endpoint}",
            f"{base}/fabric-meta/{endpoint}"
        ]
        for url in urls_to_try:
            if cancel_requested:
                return None
            try:
                print(f"  Попытка: {url}")
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    if is_meta:
                        data = resp.json()
                        if data:
                            print(f"    Данные получены с {url}")
                            return data
                    else:
                        return url
                else:
                    print(f"  Зеркало {mirror} вернуло код {resp.status_code} для {url}")
            except Exception as e:
                print(f"  Зеркало {mirror} ошибка для {url}: {e}")
                continue
    return None

def install_fabric_custom(minecraft_version: str, game_dir: str, set_status) -> bool:
    global cancel_requested, installer_process

    # ===== СНАЧАЛА НАХОДИМ ИЛИ СКАЧИВАЕМ JAVA =====
    set_status("Поиск Java...")
    java_path = get_java_executable(minecraft_version, set_status)

    # ===== ИСПРАВЛЕННАЯ ПРОВЕРКА J AVA =====
    if not java_path:
        set_status("Ошибка: Java не найдена!")
        print("  Не удалось найти Java для установки Fabric")
        return False

    # Проверяем, существует ли Java (для абсолютных путей)
    if java_path != "java" and not os.path.exists(java_path):
        set_status(f"Ошибка: Java не найдена по пути {java_path}!")
        print(f"  Java не найдена: {java_path}")
        return False

    # Если java_path == "java", проверяем через shutil.which
    if java_path == "java" and not shutil.which("java"):
        set_status("Ошибка: Java не найдена в системном PATH!")
        print("  Команда 'java' не найдена в PATH")
        return False

    print(f"  Используется Java: {java_path}")

    # Проверяем, что Java работает
    try:
        # Для команды "java" используем shell=True на Windows
        if java_path == "java" and platform.system() == "Windows":
            result = subprocess.run(["where", "java"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                set_status("Java не найдена в системе!")
                return False
            # Нашли java, теперь проверим версию
            result = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=10)
        else:
            result = subprocess.run([java_path, "-version"], capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            set_status("Java не работает!")
            return False
        print(f"  Java OK: {result.stderr.splitlines()[0] if result.stderr else 'Java работает'}")
    except Exception as e:
        print(f"  Ошибка проверки Java: {e}")
        set_status("Ошибка проверки Java")
        return False

    try:
        if cancel_requested:
            set_status("Отмена установки")
            return False

        set_status("Проверка Vanilla...")
        versions_dir = os.path.join(game_dir, "versions")
        vanilla_installed = os.path.exists(os.path.join(versions_dir, minecraft_version))
        if not vanilla_installed:
            set_status(f"Установка Vanilla {minecraft_version}...")
            try:
                minecraft_launcher_lib.install.install_minecraft_version(minecraft_version, game_dir,
                                                                         callback={"setStatus": set_status})
            except Exception as e:
                print(f"  Ошибка установки Vanilla: {e}")
                set_status(f"Ошибка установки Vanilla: {str(e)[:30]}")
                return False
            if cancel_requested:
                set_status("Отмена установки")
                return False

        set_status("Получение версий Fabric Loader...")
        loader_data = fetch_fabric_data("v2/versions/loader", set_status, is_meta=True)
        if not loader_data:
            set_status("Не удалось получить версию Fabric Loader ни с одного зеркала")
            return False

        # Для новых версий Minecraft находим совместимый loader
        latest_loader = None
        for loader in loader_data:
            if "gameVersion" in loader and str(loader["gameVersion"]) == minecraft_version:
                latest_loader = loader["version"]
                break
        if not latest_loader:
            latest_loader = loader_data[0]["version"]

        set_status(f"Loader версия: {latest_loader}")
        print(f"    Loader версия: {latest_loader}")

        set_status("Получение версии установщика...")
        installer_data = fetch_fabric_data("v2/versions/installer", set_status, is_meta=True)
        if not installer_data:
            set_status("Не удалось получить версию установщика ни с одного зеркала")
            return False
        installer_version = installer_data[0]["version"]
        set_status(f"Установщик версии: {installer_version}")
        print(f"    Установщик версии: {installer_version}")

        set_status("Скачивание установщика...")
        installer_path = os.path.join(game_dir, f"fabric-installer-{installer_version}.jar")
        downloaded = False
        if os.path.exists(installer_path) and os.path.getsize(installer_path) > 1000000:
            print(f"    Установщик уже существует: {installer_path}")
            downloaded = True

        if not downloaded:
            download_sources = [
                f"https://maven.fabricmc.net/net/fabricmc/fabric-installer/{installer_version}/fabric-installer-{installer_version}.jar",
                f"https://bmclapi2.bangbang93.com/maven/net/fabricmc/fabric-installer/{installer_version}/fabric-installer-{installer_version}.jar",
                f"https://github.com/FabricMC/fabric-installer/releases/download/{installer_version}/fabric-installer-{installer_version}.jar"
            ]
            for source_url in download_sources:
                if cancel_requested:
                    set_status("Отмена установки")
                    return False
                print(f"  Попытка скачивания с {source_url}")
                for attempt in range(3):
                    if cancel_requested:
                        set_status("Отмена установки")
                        return False
                    try:
                        r = requests.get(source_url, stream=True, timeout=30)
                        if r.status_code == 200:
                            with open(installer_path, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    if cancel_requested:
                                        f.close()
                                        if os.path.exists(installer_path):
                                            os.remove(installer_path)
                                        set_status("Отмена установки")
                                        return False
                                    f.write(chunk)
                            print(f"    Установщик скачан с {source_url} (попытка {attempt + 1})")
                            downloaded = True
                            break
                        else:
                            print(f"  Попытка {attempt + 1}: код {r.status_code}")
                    except Exception as e:
                        print(f"  Попытка {attempt + 1}: ошибка: {e}")
                        time.sleep(2)
                if downloaded:
                    break

        if not downloaded:
            set_status("Не удалось скачать установщик ни с одного источника")
            return False

        if cancel_requested:
            if os.path.exists(installer_path):
                os.remove(installer_path)
            set_status("Отмена установки")
            return False

        set_status("Запуск установщика Fabric...")

        # ===== ИСПРАВЛЕНИЕ: ФОРМИРУЕМ КОМАНДУ ПРАВИЛЬНО =====
        if java_path == "java":
            # Используем команду "java" из PATH
            command = [
                "java", "-jar", installer_path,
                "client",
                "-dir", game_dir,
                "-mcversion", minecraft_version,
                "-loader", latest_loader,
                "-noprofile", "-snapshot"
            ]
        else:
            # Используем полный путь к java
            command = [
                java_path, "-jar", installer_path,
                "client",
                "-dir", game_dir,
                "-mcversion", minecraft_version,
                "-loader", latest_loader,
                "-noprofile", "-snapshot"
            ]

        print(f"  Запуск команды: {' '.join(command)}")

        # Используем shell=True на Windows для команды "java"
        use_shell = (java_path == "java" and platform.system() == "Windows")
        installer_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=use_shell
        )

        while installer_process.poll() is None:
            if cancel_requested:
                installer_process.terminate()
                installer_process.wait()
                if os.path.exists(installer_path):
                    os.remove(installer_path)
                set_status("Отмена установки")
                installer_process = None
                return False
            time.sleep(0.1)

        stdout, stderr = installer_process.communicate()
        returncode = installer_process.returncode
        installer_process = None

        if cancel_requested:
            if os.path.exists(installer_path):
                os.remove(installer_path)
            set_status("Отмена установки")
            return False

        if returncode != 0:
            print(f" Ошибка при запуске установщика (код {returncode})")
            print("STDERR:", stderr)
            print("STDOUT:", stdout)
            set_status("Ошибка при запуске установщика")
            return False
        else:
            print("    Установщик выполнен успешно")

        if cancel_requested:
            set_status("Отмена установки")
            return False

        # Ищем созданную версию Fabric
        fabric_version_id = None
        versions_dir = os.path.join(game_dir, "versions")
        for folder in os.listdir(versions_dir):
            if folder.startswith("fabric-loader-") and folder.endswith(f"-{minecraft_version}"):
                fabric_version_id = folder
                break

        if not fabric_version_id:
            print(f" Не удалось найти Fabric версию после установки!")
            set_status("Ошибка: Fabric версия не найдена")
            return False

        fabric_version_dir = os.path.join(game_dir, "versions", fabric_version_id)
        fabric_jar_path = os.path.join(fabric_version_dir, f"{fabric_version_id}.jar")
        fabric_json_path = os.path.join(fabric_version_dir, f"{fabric_version_id}.json")
        vanilla_jar_path = os.path.join(game_dir, "versions", minecraft_version, f"{minecraft_version}.jar")

        if not os.path.exists(fabric_jar_path):
            if os.path.exists(vanilla_jar_path):
                print(f" Fabric jar не найден, копируем vanilla jar в {fabric_jar_path}")
                shutil.copy2(vanilla_jar_path, fabric_jar_path)
            else:
                print(f" Vanilla jar тоже не найден: {vanilla_jar_path}")
                set_status("Ошибка: отсутствует vanilla jar")
                return False

        if not os.path.exists(fabric_json_path):
            print(" JSON файл Fabric не найден!")
            set_status("Ошибка: Fabric не создал JSON")
            return False

        try:
            if os.path.exists(installer_path):
                os.remove(installer_path)
                print("  Установщик удалён")
        except Exception as e:
            print(f" Не удалось удалить установщик: {e}")

        set_status("Fabric успешно установлен!")
        return True

    except Exception as e:
        print(f" Критическая ошибка в install_fabric_custom: {e}")
        traceback.print_exc()
        set_status(f"Ошибка: {str(e)[:30]}")
        return False
def get_armored_forge_url(mc_version, forge_version):
    return f"https://bmclapi2.bangbang93.com/maven/net/minecraftforge/forge/{mc_version}-{forge_version}/forge-{mc_version}-{forge_version}-installer.jar"

def get_forge_versions_from_bmclapi(mc_version):
    try:
        url = f"https://bmclapi2.bangbang93.com/forge/minecraft/{mc_version}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                return [item.get('version', '') for item in data if item.get('version')]
    except Exception as e:
        print(f"Ошибка get_forge_versions_from_bmclapi: {e}")
    return []

def get_forge_versions_from_maven(mc_version):
    try:
        url = f"https://bmclapi2.bangbang93.com/maven/net/minecraftforge/forge/maven-metadata.xml"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            versions = []
            for v in root.findall(".//version"):
                v_text = v.text
                if v_text.startswith(mc_version):
                    versions.append(v_text.replace(f"{mc_version}-", ""))
            return sorted(versions, reverse=True)
    except Exception as e:
        print(f"Ошибка get_forge_versions_from_maven: {e}")
    return []

def get_forge_versions(mc_version):
    versions = get_forge_versions_from_bmclapi(mc_version)
    if versions:
        return versions
    versions = get_forge_versions_from_maven(mc_version)
    if versions:
        return versions
    forge_db = {
        "1.21.11": ["61.0.2", "61.0.1"],
        "1.21.10": ["60.1.0", "60.0.1"],
        "1.21.9": ["59.0.5", "59.0.4"],
        "1.21.8": ["58.1.0", "58.0.1"],
        "1.21.7": ["57.0.3", "57.0.2"],
        "1.21.6": ["56.0.9", "56.0.8"],
        "1.21.5": ["55.0.23", "55.0.22"],
        "1.21.4": ["54.1.0", "54.0.1"],
        "1.21.3": ["53.0.25", "53.0.24"],
        "1.21.2": ["53.0.20", "53.0.19"],
        "1.21.1": ["52.1.8", "52.0.16", "52.0.14"],
        "1.21": ["52.0.16", "52.0.14"],
        "1.20.6": ["50.1.14", "50.1.12"],
        "1.20.5": ["50.0.32", "50.0.31"],
        "1.20.4": ["49.1.0", "49.0.51"],
        "1.20.3": ["49.0.49"],
        "1.20.2": ["48.1.0", "48.0.33"],
        "1.20.1": ["47.3.11", "47.3.0", "47.2.30"],
        "1.20": ["46.0.14", "46.0.13"],
        "1.19.4": ["45.3.0", "45.2.21"],
        "1.19.3": ["44.1.23", "44.1.22"],
        "1.19.2": ["43.4.0", "43.3.8"],
        "1.19.1": ["42.0.9"],
        "1.19": ["41.1.0", "41.0.110"],
        "1.18.2": ["40.2.21", "40.2.14"],
        "1.18.1": ["39.1.2"],
        "1.18": ["38.0.17"],
        "1.17.1": ["37.1.1", "37.1.0"],
        "1.17": ["36.2.39"],
        "1.16.5": ["36.2.39", "36.2.34", "36.2.23"],
        "1.16.4": ["35.1.37"],
        "1.16.3": ["34.1.42"],
        "1.16.2": ["33.0.61"],
        "1.16.1": ["32.0.108"],
        "1.16": ["32.0.108"],
        "1.15.2": ["31.2.57"],
        "1.15.1": ["30.0.51"],
        "1.15": ["29.0.4"],
        "1.14.4": ["28.2.26"],
        "1.14.3": ["27.0.60"],
        "1.14.2": ["26.0.63"],
        "1.14.1": ["25.0.22"],
        "1.14": ["24.0.43"],
        "1.13.2": ["25.0.219"],
        "1.13.1": ["24.0.210"],
        "1.13": ["23.0.212"],
        "1.12.2": ["14.23.5.2860"],
        "1.12.1": ["14.22.1.2485"],
        "1.12": ["14.21.1.2443"],
        "1.11.2": ["13.20.1.2425"],
        "1.11": ["13.19.1.2199"],
        "1.10.2": ["12.18.3.2511"],
        "1.10": ["12.18.1.2082"],
        "1.9.4": ["12.17.0.2317"],
        "1.9": ["12.16.1.1887"],
        "1.8.9": ["11.15.1.2318"],
        "1.8.8": ["11.15.0.1655"],
        "1.8": ["11.14.4.1577"],
        "1.7.10": ["10.13.4.1614"]
    }
    return forge_db.get(mc_version, [])

def download_forge_installer(mc_version, forge_version, dest_path, set_status):
    global cancel_requested
    forge_mirrors = [
        f"https://bmclapi2.bangbang93.com/maven/net/minecraftforge/forge/{mc_version}-{forge_version}/forge-{mc_version}-{forge_version}-installer.jar",
        f"https://maven.minecraftforge.net/net/minecraftforge/forge/{mc_version}-{forge_version}/forge-{mc_version}-{forge_version}-installer.jar",
        f"https://files.minecraftforge.net/maven/net/minecraftforge/forge/{mc_version}-{forge_version}/forge-{mc_version}-{forge_version}-installer.jar",
        f"https://github.com/MinecraftForge/MinecraftForge/raw/maven/net/minecraftforge/forge/{mc_version}-{forge_version}/forge-{mc_version}-{forge_version}-installer.jar"
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Java/1.8.0'}

    for i, url in enumerate(forge_mirrors):
        if cancel_requested:
            set_status("Отмена загрузки")
            return False
        set_status(f"Загрузка Forge {mc_version}-{forge_version} (зеркало {i + 1}/4)...")
        print(f"Попытка зеркала {i+1}: {url}")
        if "com/maven" not in url:
            url = url.replace("commaven", "com/maven")

        try:
            session = get_session(url)
            r = session.get(url, headers=headers, stream=True, timeout=60)
            if r.status_code == 200:
                with open(dest_path, 'wb') as f:
                    downloaded = 0
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if cancel_requested:
                            f.close()
                            os.remove(dest_path)
                            set_status("Отмена загрузки")
                            return False
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            set_status(f"Загрузка... {downloaded // 1024 // 1024} MB")
                size = os.path.getsize(dest_path)
                if size > 2000000:
                    set_status(f"    Загружено с зеркала {i + 1}")
                    print(f"    Forge установщик загружен с зеркала {i + 1}, размер {size} байт")
                    return True
                else:
                    print(f" Файл слишком мал ({size} байт) с зеркала {i+1}")
                    set_status(f"Файл слишком мал ({size} байт)")
            else:
                print(f"  Зеркало {i + 1}: код {r.status_code}")
        except Exception as e:
            print(f"  Зеркало {i + 1}: ошибка - {str(e)[:100]}")
            continue

    set_status(" Все зеркала Forge не сработали")
    print(" Все зеркала Forge не сработали")
    return False

def install_forge(mc_version, game_dir, set_status):
    global cancel_requested, installer_process

    # ===== СНАЧАЛА НАХОДИМ ИЛИ СКАЧИВАЕМ JAVA =====
    set_status("Поиск Java для Forge...")
    java_path = get_java_executable(mc_version, set_status)

    # Проверяем, что Java найдена
    if not java_path or not os.path.exists(java_path):
        set_status("Ошибка: Java не найдена для Forge!")
        print("  Не удалось найти Java для установки Forge")
        return False

    print(f"  Используется Java для Forge: {java_path}")

    # Проверяем, что Java работает
    try:
        result = subprocess.run([java_path, "-version"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            set_status("Java не работает!")
            return False
        print(f"  Java OK: {result.stderr.splitlines()[0] if result.stderr else 'Java работает'}")
    except Exception as e:
        print(f"  Ошибка проверки Java: {e}")
        set_status("Ошибка проверки Java")
        return False

    # Получаем список версий Forge
    forge_versions = get_forge_versions(mc_version)
    if not forge_versions:
        set_status(f"Forge нет для {mc_version}!")
        print(f" Forge нет для {mc_version}")
        return False

    forge_version = forge_versions[0]
    set_status(f"Найден Forge {forge_version}")
    print(f"    Найден Forge {forge_version}")

    installer_path = os.path.join(game_dir, f"forge_installer_{mc_version}.jar")
    if os.path.exists(installer_path) and os.path.getsize(installer_path) < 1000000:
        os.remove(installer_path)

    if not os.path.exists(installer_path):
        if not download_forge_installer(mc_version, forge_version, installer_path, set_status):
            return False

    if cancel_requested:
        if os.path.exists(installer_path):
            os.remove(installer_path)
        set_status("Отмена установки")
        return False

    set_status("Установка Forge...")
    os.environ["FORGE_MAVEN_URL"] = "https://bmclapi2.bangbang93.com"

    try:
        # ИСПРАВЛЕНО: используем java_path вместо "java"
        print(f"  Запуск установщика Forge: {java_path} -jar {installer_path} --installClient {game_dir}")
        installer_process = subprocess.Popen([java_path, "-jar", installer_path, "--installClient", game_dir])

        while installer_process.poll() is None:
            if cancel_requested:
                installer_process.terminate()
                installer_process.wait()
                if os.path.exists(installer_path):
                    os.remove(installer_path)
                set_status("Отмена установки")
                installer_process = None
                return False
            time.sleep(0.1)

        returncode = installer_process.returncode
        installer_process = None

        if returncode != 0:
            raise Exception(f"Установщик вернул код {returncode}")

        set_status("Forge установлен!")
        print("    Forge установлен!")

        if os.path.exists(installer_path):
            os.remove(installer_path)
            print("  Установщик Forge удалён")

        return True

    except Exception as e:
        set_status(f"Ошибка установки: {str(e)[:20]}")
        print(f" Ошибка установки Forge: {e}")
        traceback.print_exc()
        return False

def is_forge_available(mc_version):
    return len(get_forge_versions(mc_version)) > 0

ITEM_H = 38

def get_versions():
    versions = []
    for mirror in MIRRORS:
        try:
            url = f"{mirror}/mc/game/version_manifest.json"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            r = requests.get(url, timeout=15, headers=headers)
            if r.status_code == 200:
                data = r.json()
                versions = [v['id'] for v in data['versions'] if v['type'] == 'release']
                if versions:
                    print(f"    Список версий получен с {mirror}")
                    return versions
        except Exception as e:
            print(f"Ошибка получения версий с {mirror}: {e}")
            continue
    print(" Не удалось получить версии из интернета, используется встроенный список")
    return [
        "1.21.11", "1.21.10", "1.21.9", "1.21.8", "1.21.6", "1.21.5",
        "1.21.4", "1.21.3", "1.21.2", "1.21.1", "1.21",
        "1.20.6", "1.20.5", "1.20.4", "1.20.3", "1.20.2", "1.20.1", "1.20",
        "1.19.4", "1.19.3", "1.19.2", "1.19.1", "1.19",
        "1.18.2", "1.18.1", "1.18",
        "1.17.1", "1.17",
        "1.16.5", "1.16.4", "1.16.3", "1.16.2", "1.16.1", "1.16",
        "1.15.2", "1.15.1", "1.15",
        "1.14.4", "1.14.3", "1.14.2", "1.14.1", "1.14",
        "1.13.2", "1.13.1", "1.13",
        "1.12.2", "1.12.1", "1.12",
        "1.11.2", "1.11",
        "1.10.2", "1.10",
        "1.9.4", "1.9",
        "1.8.9", "1.8.8", "1.8",
        "1.7.10"
    ]

all_versions = get_versions()

def load_settings():
    global username, ram_gb, v_idx, fullscreen, delete_incompatible_mods, download_standard_mods
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                d = json.load(f)
                username = d.get("username", "Turbo_Player")
                ram_gb = d.get("ram", 4)
                v_idx = d.get("v_idx", 0)
                fullscreen = d.get("fullscreen", False)
                delete_incompatible_mods = d.get("delete_incompatible_mods", True)
                download_standard_mods = d.get("download_standard_mods", True)
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
    else:
        username, ram_gb, v_idx, fullscreen = "Turbo_Player", 4, 0, False
        delete_incompatible_mods = True
        download_standard_mods = True
    return username, ram_gb, v_idx, fullscreen
# <-- ИЗМЕНЕНО: теперь распаковываем 4 значения
delete_incompatible_mods = True
download_standard_mods = True
username, ram_gb, v_idx, fullscreen = load_settings()

import atexit
import signal

def on_launcher_exit():
    """Вызывается при закрытии лаунчера или выключении ПК"""
    global username
    print("  Лаунчер закрывается, удаляем игрока из онлайна...")
    try:
        update_online_count(username, False)
    except:
        pass
    try:
        stop_discord_presence()
    except:
        pass
    print("    Игрок удалён из онлайна")

atexit.register(on_launcher_exit)

def signal_handler(signum, frame):
    on_launcher_exit()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

import discord
from discord.ext import commands
import threading

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN_FOR_BOT")

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
bot_ready = False

# Файл для хранения информации об игроках
PLAYER_INFO_FILE = os.path.join(GAME_DIR, "player_info.json")

def get_players_from_jsonbin():
    """Получает список игроков из JSONBin"""
    try:
        headers = {"X-Master-Key": JSONBIN_API_KEY}
        resp = requests.get(JSONBIN_URL, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json().get("record", {"players": []})
            return data.get("players", [])
    except Exception as e:
        print(f"Ошибка получения игроков: {e}")
    return []

def get_launcher_version():
    """Получает версию лаунчера"""
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r') as f:
            return f.read().strip()
    return "1.0.0"

def save_player_info_to_file(username, mc_version, loader):
    """Сохраняет информацию об игроке"""
    try:
        player_data = {}
        if os.path.exists(PLAYER_INFO_FILE):
            with open(PLAYER_INFO_FILE, 'r', encoding='utf-8') as f:
                player_data = json.load(f)

        player_data[username] = {
            "minecraft_version": mc_version,
            "loader": loader,
            "last_play": time.time()
        }

        with open(PLAYER_INFO_FILE, 'w', encoding='utf-8') as f:
            json.dump(player_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка сохранения информации об игроке: {e}")

@bot.event
async def on_ready():
    global bot_ready
    bot_ready = True
    print(f'    Discord бот запущен как {bot.user}')
    print(f'  Команды бота: !list, !player_delete [ник], !player_check [ник]')

@bot.command(name='list')
async def list_players(ctx):
    """Показывает список игроков онлайн"""
    try:
        players = get_players_from_jsonbin()
        count = len(players)

        embed = discord.Embed(
            title="Игроки онлайн",
            color=0x00ff00
        )

        if count == 0:
            embed.description = "Никого нет в сети"
        else:
            player_list = "\n".join([f"• {p}" for p in players])
            embed.description = player_list
            embed.set_footer(text=f"Всего: {count} игроков")

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f" Ошибка: {e}")

@bot.command(name='player_delete')
async def delete_player(ctx, nickname: str):
    """Удаляет игрока из онлайна (только админ)"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(" Только администраторы могут использовать эту команду!")
        return

    try:
        headers = {"X-Master-Key": JSONBIN_API_KEY, "Content-Type": "application/json"}
        resp = requests.get(JSONBIN_URL, headers=headers, timeout=10)

        if resp.status_code == 200:
            data = resp.json().get("record", {"players": []})
            players = data.get("players", [])

            if nickname in players:
                players.remove(nickname)
                new_data = {
                    "players": players,
                    "count": len(players),
                    "last_update": time.time()
                }
                put_resp = requests.put(JSONBIN_URL, headers=headers, json=new_data, timeout=10)

                if put_resp.status_code == 200:
                    embed = discord.Embed(
                        title="    Игрок удалён",
                        description=f"**{nickname}** удалён из онлайна",
                        color=0x00ff00
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(" Ошибка обновления данных")
            else:
                await ctx.send(f" Игрок **{nickname}** не найден в онлайне")
        else:
            await ctx.send(" Ошибка получения данных")
    except Exception as e:
        await ctx.send(f" Ошибка: {e}")

@bot.command(name='player_check')
async def check_player(ctx, nickname: str = None):
    """Показывает информацию об игроке или версию лаунчера"""
    try:
        if nickname is None:
            launcher_version = get_launcher_version()
            players = get_players_from_jsonbin()

            embed = discord.Embed(
                title="  Turbo Launcher",
                description=f"**Версия лаунчера:** {launcher_version}",
                color=0x00ff00
            )
            embed.add_field(name=" Онлайн", value=f"{len(players)} игроков", inline=False)
            embed.set_footer(text="Turbo Launcher")
            await ctx.send(embed=embed)
            return

        players = get_players_from_jsonbin()
        is_online = nickname in players

        mc_version = "Неизвестно"
        loader = "Неизвестно"

        if os.path.exists(PLAYER_INFO_FILE):
            with open(PLAYER_INFO_FILE, 'r', encoding='utf-8') as f:
                player_data = json.load(f)
            if nickname in player_data:
                mc_version = player_data[nickname].get("minecraft_version", "Неизвестно")
                loader = player_data[nickname].get("loader", "Неизвестно")

        embed = discord.Embed(
            title=f"  Информация об игроке: {nickname}",
            color=0x00ff00 if is_online else 0xff0000
        )
        embed.add_field(name="  Статус", value="В сети" if is_online else "Не в сети", inline=True)
        embed.add_field(name="Версия Minecraft", value=mc_version, inline=True)
        embed.add_field(name="  Загрузчик", value=loader, inline=True)

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f" Ошибка: {e}")

def run_discord_bot():
    """Запускает Discord бота в отдельном потоке"""
    try:
        bot.run(BOT_TOKEN)
    except Exception as e:
        print(f" Ошибка запуска Discord бота: {e}")

# Запускаем бота, если токен указан
if BOT_TOKEN != "ВСТАВЬ_ТОКЕН_СЮДА":
    bot_thread = threading.Thread(target=run_discord_bot, daemon=True)
    bot_thread.start()
    print("  Discord бот запускается...")
else:
    print(" Токен Discord бота не настроен! Команды не будут работать.")
def save_settings():
    global username, ram_gb, v_idx, fullscreen, delete_incompatible_mods, download_standard_mods
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "username": username,
                "ram": ram_gb,
                "v_idx": v_idx,
                "fullscreen": fullscreen,
                "delete_incompatible_mods": delete_incompatible_mods,
                "download_standard_mods": download_standard_mods
            }, f, indent=4)
    except Exception as e:
        print(f"Ошибка сохранения настроек: {e}")

status = "Готов"
is_running = False
current_tab = "ИГРАТЬ"
loaders = ["Vanilla", "Fabric", "Forge"]
l_idx = 0
show_dropdown = False
scroll_y = 0
active_input = False
dragging_ram = False
dragging_scroll = False

def add_camera_control_to_minecraft(game_dir, set_status):
    try:
        options_file = os.path.join(game_dir, "options.txt")
        if os.path.exists(options_file):
            with open(options_file, 'r', encoding='utf-8') as f:
                content = f.read()
            if "key_C:" not in content:
                with open(options_file, 'a', encoding='utf-8') as f:
                    f.write("\nkey_C:key.keyboard.c\n")
                    f.write("key.zoom:key.keyboard.z\n")
                set_status("Добавлено управление камерой (C)")
                return True
    except Exception as e:
        print(f"Ошибка добавления управления: {e}")
    return False

def monitor_game_process(proc):
    global is_running, minecraft_process, cancel_requested

    # Обновляем Discord - показываем что играет через лаунчер
    update_discord_presence(
        "Играет через Turbo Launcher",
        f"Minecraft {all_versions[v_idx]}",
        start_time=int(time.time())
    )

    proc.wait()
    minecraft_process = None
    is_running = False
    cancel_requested = False
    print("    Игра завершена")
    update_online_count(username, False)

    # Возвращаем статус в лаунчер
    update_discord_presence("В лаунчере", "")

def check_loader_compatibility(mc_version, loader):
    """
    Проверяет, совместим ли выбранный загрузчик с версией Minecraft
    Возвращает (is_compatible, suggested_loader)
    is_compatible = False -> отмена запуска
    is_compatible = True -> можно запускать с suggested_loader
    """
    try:
        if mc_version.startswith('1.'):
            parts = mc_version.split('.')
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
        else:
            # Новые версии (26.x и выше) — считаем совместимыми
            return True, loader
    except:
        return True, loader

    # ========== ПРОВЕРКА ДЛЯ FABRIC ==========
    if loader == "Fabric":
        # Fabric официально работает с 1.14+, но стабильно с 1.16.5
        if minor < 14:
            answer = messagebox.askyesno(
                " Fabric не поддерживается",
                f"Minecraft {mc_version} НЕ ПОДДЕРЖИВАЕТ Fabric!\n\n"
                f"• Fabric работает только с версиями 1.14 и выше\n"
                f"• Стабильная работа гарантирована с 1.16.5\n\n"
                f"Запустить с Vanilla вместо Fabric?",
                icon='warning'
            )
            if answer:
                return True, "Vanilla"
            else:
                return False, loader

        elif minor == 14 or minor == 15:
            answer = messagebox.askyesno(
                " Fabric может работать нестабильно",
                f"Minecraft {mc_version} имеет ОГРАНИЧЕННУЮ поддержку Fabric!\n\n"
                f"• Fabric API может работать, но моды (Sodium, Iris) — НЕТ\n"
                f"• Рекомендуется использовать 1.16.5 или выше\n\n"
                f"Продолжить с Fabric?",
                icon='warning'
            )
            if not answer:
                # Пользователь отказался, предлагаем Vanilla
                vanilla_answer = messagebox.askyesno(
                    "Запустить с Vanilla?",
                    f"Запустить Minecraft {mc_version} без модов (Vanilla)?",
                    icon='question'
                )
                if vanilla_answer:
                    return True, "Vanilla"
                else:
                    return False, loader
            return True, loader

        elif minor == 16 and patch < 5:
            answer = messagebox.askyesno(
                " Fabric может работать нестабильно",
                f"Minecraft {mc_version} имеет ОГРАНИЧЕННУЮ поддержку Fabric!\n\n"
                f"• Стабильная работа гарантирована с 1.16.5\n"
                f"• Моды (Sodium, Iris) могут не работать\n\n"
                f"Продолжить с Fabric?",
                icon='warning'
            )
            if not answer:
                vanilla_answer = messagebox.askyesno(
                    "Запустить с Vanilla?",
                    f"Запустить Minecraft {mc_version} без модов (Vanilla)?",
                    icon='question'
                )
                if vanilla_answer:
                    return True, "Vanilla"
                else:
                    return False, loader
            return True, loader

    # ========== ПРОВЕРКА ДЛЯ FORGE ==========
    if loader == "Forge":
        # Forge работает с 1.1+
        if minor < 1:
            answer = messagebox.askyesno(
                " Forge не поддерживается",
                f"Minecraft {mc_version} НЕ ПОДДЕРЖИВАЕТ Forge!\n\n"
                f"• Forge работает только с версиями 1.1 и выше\n\n"
                f"Запустить с Vanilla вместо Forge?",
                icon='warning'
            )
            if answer:
                return True, "Vanilla"
            else:
                return False, loader

        # Предупреждение для 1.13-1.15 (Forge может быть нестабилен)
        if 13 <= minor <= 15:
            answer = messagebox.askyesno(
                " Forge может работать нестабильно",
                f"Forge для Minecraft {mc_version} может работать нестабильно!\n\n"
                f"• Рекомендуется использовать 1.12.2 или 1.16.5+\n\n"
                f"Продолжить с Forge?",
                icon='warning'
            )
            if not answer:
                vanilla_answer = messagebox.askyesno(
                    "Запустить с Vanilla?",
                    f"Запустить Minecraft {mc_version} без Forge (Vanilla)?",
                    icon='question'
                )
                if vanilla_answer:
                    return True, "Vanilla"
                else:
                    return False, loader
            return True, loader

    return True, loader
def show_incompatible_warning():
    """Показывает предупреждение о возможных проблемах и возвращает True (продолжить)"""
    return messagebox.askokcancel(
        "Предупреждение о совместимости",
        "⚠️ ВНИМАНИЕ! ⚠️\n\n"
        "У вас включено: 'Скачивать стандартные моды'\n"
        "У вас выключено: 'Удалять несовместимые моды'\n\n"
        "ЭТО МОЖЕТ ВЫЗВАТЬ ПРОБЛЕМЫ!\n\n"
        "При смене версии Minecraft старые моды НЕ БУДУТ УДАЛЕНЫ,\n"
        "что может привести к конфликтам и вылетам игры.\n\n"
        "Рекомендуется включить 'Удалять несовместимые моды'.\n\n"
        "Вы уверены, что хотите продолжить?",
        icon='warning'
    )


def run_launch_logic():
    global status, is_running, cancel_requested, minecraft_process, installer_process, l_idx
    try:
        is_running = True
        cancel_requested = False
        ver = all_versions[v_idx]
        loader = loaders[l_idx]

        # ===== ПРОВЕРКА СОВМЕСТИМОСТИ ЗАГРУЗЧИКА =====
        is_compatible, suggested_loader = check_loader_compatibility(ver, loader)

        if not is_compatible:
            status = "Отменено (несовместимый загрузчик)"
            is_running = False
            return

        if suggested_loader != loader:
            l_idx = loaders.index(suggested_loader)
            loader = suggested_loader
            status = f"Автоматически переключено на {loader} для {ver}"
            print(f"  Переключено на {loader} для совместимости с {ver}")

        def set_status(t):
            global status
            status = t

        print(f"\n  Запуск: версия {ver}, загрузчик {loader}")

        if ver is None:
            status = "Ошибка: версия не выбрана!"
            is_running = False
            return

        if loader == "Forge" and not is_forge_available(ver):
            status = f"Forge нет для {ver}!"
            print(f" Forge нет для {ver}")
            is_running = False
            return

        if cancel_requested:
            status = "Отменено"
            is_running = False
            return

        set_status("Поиск...")
        installed = minecraft_launcher_lib.utils.get_installed_versions(GAME_DIR)
        print(f"Установленные версии: {[v['id'] for v in installed]}")

        target_id = None

        if loader == "Fabric":
            for v in installed:
                if v['id'].startswith("fabric-loader-") and v['id'].endswith(f"-{ver}"):
                    target_id = v['id']
                    break
        elif loader == "Forge":
            for v in installed:
                if v['id'].startswith(f"{ver}-forge"):
                    target_id = v['id']
                    break
        else:
            for v in installed:
                if v['id'] == ver:
                    target_id = v['id']
                    break

        if target_id is None:
            print(f" {loader} для {ver} не найден, начинаем установку")

            max_retries = 3
            vanilla_installed = False
            for attempt in range(max_retries):
                if cancel_requested:
                    status = "Отменено"
                    is_running = False
                    return

                try:
                    set_status(f"Установка Vanilla {ver} (попытка {attempt + 1}/{max_retries})...")
                    minecraft_launcher_lib.install.install_minecraft_version(ver, GAME_DIR,
                                                                             callback={"setStatus": set_status})
                    vanilla_installed = True
                    break
                except InvalidChecksum as e:
                    if attempt < max_retries - 1:
                        print(f" Ошибка контрольной суммы, повторная попытка {attempt + 2}/{max_retries}...")
                        set_status(f"Ошибка загрузки, повтор {attempt + 2}/{max_retries}...")
                        time.sleep(2)
                    else:
                        print(f" Не удалось установить Vanilla {ver} после {max_retries} попыток")
                        status = f"Ошибка установки {ver}"
                        is_running = False
                        return
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f" Ошибка при установке Vanilla: {e}. Повтор через 2 сек...")
                        set_status(f"Ошибка, повтор {attempt + 2}/{max_retries}...")
                        time.sleep(2)
                    else:
                        print(f" Не удалось установить Vanilla {ver} после {max_retries} попыток")
                        status = f"Ошибка установки {ver}"
                        is_running = False
                        return

            if cancel_requested:
                status = "Отменено"
                is_running = False
                return

            if loader == "Fabric":
                set_status("Установка Fabric...")
                if not install_fabric_custom(ver, GAME_DIR, set_status):
                    if not cancel_requested:
                        status = f" Ошибка установки Fabric для {ver}!"
                    is_running = False
                    return
                installed = minecraft_launcher_lib.utils.get_installed_versions(GAME_DIR)
                print(f"После установки: {[v['id'] for v in installed]}")
                found = False
                for v in installed:
                    if v['id'].startswith("fabric-loader-") and v['id'].endswith(f"-{ver}"):
                        target_id = v['id']
                        found = True
                        break
                if not found:
                    versions_dir = os.path.join(GAME_DIR, "versions")
                    for folder in os.listdir(versions_dir):
                        if folder.startswith("fabric-loader-") and folder.endswith(f"-{ver}"):
                            target_id = folder
                            found = True
                            break
                if not found:
                    print(" Не удалось найти Fabric версию после установки!")
                    status = f" Fabric не найден после установки для {ver}!"
                    is_running = False
                    return

            elif loader == "Forge":
                set_status("Установка Forge...")
                if not install_forge(ver, GAME_DIR, set_status):
                    if not cancel_requested:
                        status = f" Ошибка установки Forge для {ver}!"
                    is_running = False
                    return
                installed = minecraft_launcher_lib.utils.get_installed_versions(GAME_DIR)
                print(f"После установки: {[v['id'] for v in installed]}")
                for v in installed:
                    if v['id'].startswith(f"{ver}-forge"):
                        target_id = v['id']
                        break
                if target_id is None:
                    status = f" Forge не найден после установки для {ver}!"
                    is_running = False
                    return
            else:
                target_id = ver

        if target_id is None:
            status = "КРИТИЧЕСКАЯ ОШИБКА: target_id = None"
            print(" target_id is None")
            is_running = False
            return

        # Фикс для Forge 1.21.11
        if ver == "1.21.11" and loader == "Forge":
            set_status("Применение фикса для Forge 1.21.11...")
            versions_dir = os.path.join(GAME_DIR, "versions")
            forge_folders = [f for f in os.listdir(versions_dir) if 'forge' in f.lower() and '1.21.11' in f]
            if forge_folders:
                forge_dir = os.path.join(versions_dir, forge_folders[0])
                vanilla_dir = os.path.join(versions_dir, "1.21.11")
                vanilla_jar = os.path.join(vanilla_dir, "1.21.11.jar")
                forge_jar = os.path.join(forge_dir, f"{forge_folders[0]}.jar")
                if os.path.exists(vanilla_jar) and not os.path.exists(forge_jar):
                    shutil.copy2(vanilla_jar, forge_jar)
                    set_status("    Фикс применён")
                    print("    Фикс Forge 1.21.11 применён")

        # Дополнительная проверка для Fabric (на случай отсутствия jar)
        if loader == "Fabric":
            fabric_jar_path = os.path.join(GAME_DIR, "versions", target_id, f"{target_id}.jar")
            vanilla_jar_path = os.path.join(GAME_DIR, "versions", ver, f"{ver}.jar")
            if not os.path.exists(fabric_jar_path) and os.path.exists(vanilla_jar_path):
                print(f" Fabric jar отсутствует, копируем из vanilla в {fabric_jar_path}")
                os.makedirs(os.path.dirname(fabric_jar_path), exist_ok=True)
                shutil.copy2(vanilla_jar_path, fabric_jar_path)

        # ===== УПРАВЛЕНИЕ МОДАМИ =====
        mods_dir = os.path.join(GAME_DIR, "mods")
        if loader == "Fabric":
            # === ПРЕДУПРЕЖДЕНИЕ ДЛЯ FABRIC (ТОЛЬКО ЗДЕСЬ!) ===
            if download_standard_mods and not delete_incompatible_mods:
                if not show_incompatible_warning():
                    status = "Отменено пользователем"
                    is_running = False
                    return

            if download_standard_mods:
                last_version = get_last_fabric_version()
                need_download = False

                if delete_incompatible_mods and last_version != ver:
                    print(f"  Версия Fabric изменилась: было {last_version}, стало {ver}. Очистка mods (включена).")
                    clear_mods_folder()
                    need_download = True
                elif not delete_incompatible_mods and last_version != ver:
                    print(f"  Версия Fabric изменилась: было {last_version}, стало {ver}, но удаление модов отключено.")
                    need_download = True
                else:
                    if os.path.exists(mods_dir):
                        jar_files = [f for f in os.listdir(mods_dir) if f.endswith(".jar")]
                        if len(jar_files) == 0:
                            print(" Папка mods пуста, скачиваем моды.")
                            need_download = True
                        else:
                            print(f"    Найдено {len(jar_files)} модов, пропускаем скачивание.")
                            need_download = False
                    else:
                        need_download = True

                if need_download:
                    if delete_incompatible_mods:
                        if os.path.exists(mods_dir):
                            for file in os.listdir(mods_dir):
                                if file.endswith(".jar"):
                                    try:
                                        os.remove(os.path.join(mods_dir, file))
                                        print(f"  Удалён старый мод: {file}")
                                    except:
                                        pass
                    else:
                        print("  Старые моды НЕ удалены (галочка выключена)")

                    set_status("Скачивание совместимых модов для Fabric...")
                    success = install_fabric_mods(ver, GAME_DIR, set_status)
                    if success:
                        set_status("Моды для Fabric готовы")
                        set_last_fabric_version(ver)
                    else:
                        set_status("Ошибка при установке модов")
                        print("  ОШИБКА: не удалось установить моды")
                else:
                    set_status("Моды проверены")
            else:
                set_status("Скачивание модов отключено в настройках")
                print("  Скачивание стандартных модов отключено пользователем")
        else:
            clear_mods_folder()
            if os.path.exists(LAST_FABRIC_VERSION_FILE):
                os.remove(LAST_FABRIC_VERSION_FILE)

        version_dir = os.path.join(GAME_DIR, "versions", target_id)
        if not os.path.exists(version_dir):
            status = f"Папка версии {target_id} не найдена!"
            print(f" Папка версии {target_id} не найдена")
            is_running = False
            return

        if cancel_requested:
            status = "Отменено"
            is_running = False
            return

        set_status(f"Запуск {target_id}...")

        java_executable = get_java_executable(ver, set_status)
        if not java_executable:
            set_status("Не удалось найти подходящую Java")
            is_running = False
            return

        cpu_count = os.cpu_count() or 4

        def is_modern_version(version_str):
            try:
                if not version_str.startswith('1.'):
                    return True
                parts = version_str.split('.')
                if len(parts) >= 2 and parts[0] == '1':
                    major = int(parts[1])
                    return major >= 17
            except:
                pass
            return False

        # ===== JVM АРГУМЕНТЫ С ФИКСОМ ДЛЯ 1.8.9 =====
        old_versions = ["1.3.2", "1.4.7", "1.5.2", "1.6.4", "1.7.10", "1.8", "1.8.8", "1.8.9"]

        if ver in old_versions:
            jvm_args = [
                f"-Xmx{ram_gb}G",
                f"-Xms{ram_gb}G",
                "-Dorg.lwjgl.opengl.Display.allowSoftwareOpenGL=true",
                "-Dorg.lwjgl.opengl.Display.enableOSXFullscreenModePatch=true",
                "-Dorg.lwjgl.opengl.Window.undecorated=false",
                "-Djava.awt.headless=false",
                "-Dfile.encoding=UTF-8"
            ]
            print(f"    Использованы специальные JVM аргументы для {ver}")
        elif is_modern_version(ver):
            jvm_args = [
                f"-Xmx{ram_gb}G",
                f"-Xms{ram_gb}G",
                "-XX:+UseZGC",
                "-XX:+ParallelRefProcEnabled",
                "-XX:MaxGCPauseMillis=50",
                "-XX:+UnlockExperimentalVMOptions",
                "-XX:+DisableExplicitGC",
                "-XX:+AlwaysPreTouch",
                f"-XX:ParallelGCThreads={cpu_count}",
                "-XX:ConcGCThreads=4",
                "-XX:ReservedCodeCacheSize=1024M",
                "-XX:+UseStringDeduplication",
                "-Dfile.encoding=UTF-8"
            ]
        else:
            jvm_args = [
                f"-Xmx{ram_gb}G",
                f"-Xms{ram_gb}G",
                "-XX:+UseG1GC",
                "-XX:+ParallelRefProcEnabled",
                "-XX:MaxGCPauseMillis=50",
                "-XX:+UnlockExperimentalVMOptions",
                "-XX:+DisableExplicitGC",
                "-XX:+AlwaysPreTouch",
                f"-XX:ParallelGCThreads={cpu_count}",
                "-XX:ConcGCThreads=4",
                "-XX:ReservedCodeCacheSize=1024M",
                "-XX:+UseStringDeduplication",
                "-Dfile.encoding=UTF-8",
                "-Dorg.lwjgl.opengl.Display.allowSoftwareOpenGL=true"
            ]

        # ===== АРГУМЕНТЫ ОКНА =====
        print(f"fullscreen = {fullscreen}")

        if fullscreen:
            game_args = ["--fullscreen"]
        elif ver in old_versions:
            game_args = []
            print(f" Для версии {ver} убраны аргументы --width/--height")
        else:
            game_args = ["--width", "854", "--height", "480"]

        # ===== АВТОМАТИЧЕСКОЕ ВКЛЮЧЕНИЕ ELY.BY =====
        def get_authlib_version(mc_version):
            try:
                if mc_version.startswith('1.'):
                    parts = mc_version.split('.')
                    minor = int(parts[1]) if len(parts) > 1 else 0
                    patch = int(parts[2]) if len(parts) > 2 else 0
                    if minor > 20 or (minor == 20 and patch >= 4):
                        return "1.2.7"
                    elif minor == 20:
                        return "1.2.4"
                    elif minor == 19 and patch >= 4:
                        return "1.2.2"
                    elif minor == 19:
                        return "1.2.1"
                    elif minor >= 16:
                        return "1.1.47"
                    else:
                        return "1.1.46"
                else:
                    major = int(mc_version.split('.')[0])
                    if major >= 26:
                        return "1.2.7"
                    else:
                        return "1.2.7"
            except:
                return "1.2.7"

        authlib_version = get_authlib_version(ver)
        authlib_filename = f"authlib-injector-{authlib_version}.jar"
        authlib_path = os.path.join(GAME_DIR, authlib_filename)

        if not os.path.exists(authlib_path):
            print(f"  Скачивание authlib-injector v{authlib_version}...")
            set_status(f"Загрузка Ely.by v{authlib_version}...")
            download_urls = [
                f"https://github.com/yushijinhun/authlib-injector/releases/download/v{authlib_version}/authlib-injector-{authlib_version}.jar",
                f"https://github.moeyy.xyz/https://github.com/yushijinhun/authlib-injector/releases/download/v{authlib_version}/authlib-injector-{authlib_version}.jar",
            ]
            downloaded = False
            for url in download_urls:
                try:
                    r = requests.get(url, stream=True, timeout=30)
                    if r.status_code == 200:
                        with open(authlib_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                        downloaded = True
                        break
                except:
                    continue
            if not downloaded:
                fallback_url = "https://github.com/yushijinhun/authlib-injector/releases/latest/download/authlib-injector.jar"
                try:
                    r = requests.get(fallback_url, stream=True, timeout=30)
                    if r.status_code == 200:
                        authlib_path = os.path.join(GAME_DIR, "authlib-injector-latest.jar")
                        with open(authlib_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                except:
                    pass

        if os.path.exists(authlib_path) and os.path.getsize(authlib_path) > 100000:
            javaagent_arg = f"-javaagent:{authlib_path}=https://authserver.ely.by"
            jvm_args.insert(0, javaagent_arg)
            print(f"    Ely.by включен")
        else:
            print(" Ely.by не будет работать")

        options = {
            "username": username,
            "uuid": str(uuid.uuid4()),
            "token": "0",
            "jvmArguments": jvm_args,
            "gameArguments": game_args,
            "executablePath": java_executable
        }

        cmd = minecraft_launcher_lib.command.get_minecraft_command(target_id, GAME_DIR, options)
        print(f"Команда запуска: {' '.join(cmd)}")

        if fullscreen and "--fullscreen" not in cmd:
            cmd.append("--fullscreen")
            print("    --fullscreen добавлен принудительно")

        # ===== ЗАПУСК =====
        if os.name == 'nt':
            log_file = os.path.join(GAME_DIR, "minecraft_latest.log")
            print(f"  Лог сохраняется в: {log_file}")

            minecraft_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            def read_output(pipe, log_f):
                for line_bytes in pipe:
                    if cancel_requested:
                        break
                    try:
                        line = line_bytes.decode('utf-8', errors='replace').strip()
                    except:
                        line = str(line_bytes)[:200]
                    if line:
                        print(f"{line}")
                        with open(log_f, 'a', encoding='utf-8') as f:
                            f.write(f"{line}\n")

            threading.Thread(target=read_output, args=(minecraft_process.stdout, log_file), daemon=True).start()
            threading.Thread(target=read_output, args=(minecraft_process.stderr, log_file), daemon=True).start()
            threading.Thread(target=monitor_game_process, args=(minecraft_process,), daemon=True).start()

            if ver in old_versions:
                def force_show_window():
                    time.sleep(3)
                    try:
                        import win32gui
                        import win32con
                        def enum_windows_callback(hwnd, windows):
                            title = win32gui.GetWindowText(hwnd)
                            class_name = win32gui.GetClassName(hwnd)
                            if 'Minecraft' in title or 'LWJGL' in class_name:
                                windows.append((hwnd, title))

                        windows = []
                        win32gui.EnumWindows(enum_windows_callback, windows)
                        for hwnd, title in windows:
                            print(f"  Найдено окно: {title}")
                            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 0, 0, 0, 0,
                                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
                            win32gui.SetForegroundWindow(hwnd)
                            print(f"    Окно Minecraft принудительно показано!")
                            return
                        print(" Окно Minecraft не найдено")
                    except ImportError:
                        print(" pywin32 не установлен, окно может не появиться")
                    except Exception as e:
                        print(f" Ошибка при показе окна: {e}")

                threading.Thread(target=force_show_window, daemon=True).start()

            pygame.time.wait(3000)

            if minecraft_process is not None and minecraft_process.poll() is not None:
                print(" Игра закрылась сразу!")
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        last_lines = f.readlines()[-20:]
                        print("\n  ПОСЛЕДНИЕ 20 СТРОК ЛОГА:")
                        print("-" * 50)
                        for line in last_lines:
                            print(line.strip())
                        print("-" * 50)
                except Exception as e:
                    print(f"Не удалось прочитать лог: {e}")
                status = "Игра закрылась сразу"
                is_running = False
                minecraft_process = None
            else:
                print(f"    Игра запущена, PID: {minecraft_process.pid}")
                set_status("В игре!")
                update_online_count(username, True)

    except Exception as e:
        print(traceback.format_exc())
        status = f"Ошибка: {str(e)[:30]}"
        is_running = False
        cancel_requested = False
        minecraft_process = None
        installer_process = None
class LanguageSwitcher:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        # Кнопки внутри овала
        self.buttons = {
            "ru": pygame.Rect(x + 5, y + 3, 35, height - 6),
            "en": pygame.Rect(x + width - 40, y + 3, 35, height - 6)
        }
        self.anim_progress = 0
        self.target_progress = 0
        self.anim_speed = 0.15
        self.hover_ru = False
        self.hover_en = False

    def update(self, dt):
        self.target_progress = 1 if current_lang == "en" else 0
        self.anim_progress += (self.target_progress - self.anim_progress) * self.anim_speed * dt
        self.anim_progress = max(0, min(1, self.anim_progress))

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            mx, my = pygame.mouse.get_pos()
            self.hover_ru = self.buttons["ru"].collidepoint(mx, my)
            self.hover_en = self.buttons["en"].collidepoint(mx, my)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for lang, btn_rect in self.buttons.items():
                if btn_rect.collidepoint(event.pos):
                    return lang
        return None

    def draw(self, screen):
        # Только овал! Без квадратов!
        # Фоновый овал
        pygame.draw.rect(screen, (25, 30, 25), self.rect, border_radius=40)
        pygame.draw.rect(screen, (50, 70, 50), self.rect, 1, border_radius=40)

        # Скользящий индикатор (тоже овальный)
        indicator_width = self.buttons["ru"].width
        indicator_x = self.buttons["ru"].x + self.anim_progress * (self.buttons["en"].x - self.buttons["ru"].x)
        indicator_rect = pygame.Rect(indicator_x, self.buttons["ru"].y, indicator_width, self.buttons["ru"].height)

        # Зелёный индикатор
        pygame.draw.rect(screen, (0, 200, 80), indicator_rect, border_radius=20)

        # Текст кнопок
        ru_color = (255, 255, 255) if current_lang == "ru" else (150, 150, 150)
        en_color = (255, 255, 255) if current_lang == "en" else (150, 150, 150)

        # Эффект при наведении
        if self.hover_ru and current_lang != "ru":
            ru_color = (100, 255, 100)
        if self.hover_en and current_lang != "en":
            en_color = (100, 255, 100)

        ru_text = font_small.render("RU", True, ru_color)
        en_text = font_small.render("EN", True, en_color)

        screen.blit(ru_text, (self.buttons["ru"].centerx - ru_text.get_width() // 2,
                              self.buttons["ru"].centery - ru_text.get_height() // 2))
        screen.blit(en_text, (self.buttons["en"].centerx - en_text.get_width() // 2,
                              self.buttons["en"].centery - en_text.get_height() // 2))

pygame.init()

start_discord_presence()
WIDTH, HEIGHT = 940, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.DOUBLEBUF | pygame.HWSURFACE)
pygame.display.set_caption("Turbo Launcher")
# После pygame.display.set_mode()
icon = pygame.image.load("turbolauncher.ico")  # или .png
pygame.display.set_icon(icon)

# Типы курсоров
CURSOR_NORMAL = pygame.SYSTEM_CURSOR_ARROW  # обычная стрелка
CURSOR_HAND = pygame.SYSTEM_CURSOR_HAND  # рука (указательный палец)
CURSOR_IBEAM = pygame.SYSTEM_CURSOR_IBEAM  # текстовый курсор (I-beam)
CURSOR_WAIT = pygame.SYSTEM_CURSOR_WAIT  # песочные часы/загрузка

def update_cursor(mx, my):
    """Обновляет вид курсора в зависимости от того, на что наведён курсор"""
    global show_dropdown, active_input, current_tab_index

    # Поле ввода ника (текстовый курсор)
    if current_tab_index == 0:
        nick_rect = pygame.Rect(40, 90, 240, 45)
        if nick_rect.collidepoint(mx, my):
            pygame.mouse.set_cursor(CURSOR_IBEAM)
            return

    # Кнопка "ИГРАТЬ/ОТМЕНА"
    play_rect = pygame.Rect(WIDTH // 2 - 110, 505, 220, 60)
    if play_rect.collidepoint(mx, my):
        pygame.mouse.set_cursor(CURSOR_HAND)
        return

    # Кнопка выбора версии
    v_btn_rect = pygame.Rect(play_rect.x - 220, 505, 210, 60)
    if v_btn_rect.collidepoint(mx, my):
        pygame.mouse.set_cursor(CURSOR_HAND)
        return

    # Кнопка выбора ядра
    l_rect = pygame.Rect(play_rect.right + 10, 505, 140, 60)
    if l_rect.collidepoint(mx, my):
        pygame.mouse.set_cursor(CURSOR_HAND)
        return

    # Кнопка-папка
    folder_rect = pygame.Rect(850, 512, 40, 40)
    if folder_rect.collidepoint(mx, my):
        pygame.mouse.set_cursor(CURSOR_HAND)
        return

    # Вкладки
    if pygame.Rect(40, 0, 150, 60).collidepoint(mx, my) or pygame.Rect(200, 0, 150, 60).collidepoint(mx, my):
        pygame.mouse.set_cursor(CURSOR_HAND)
        return

    # Переключатель языка
    if hasattr(lang_switcher, 'buttons'):
        if lang_switcher.buttons["ru"].collidepoint(mx, my) or lang_switcher.buttons["en"].collidepoint(mx, my):
            pygame.mouse.set_cursor(CURSOR_HAND)
            return

    # Чекбоксы в настройках
    if current_tab_index == 1:
        # Fullscreen чекбокс
        checkbox_rect = pygame.Rect(70, 280, 20, 20)
        if checkbox_rect.collidepoint(mx, my):
            pygame.mouse.set_cursor(CURSOR_HAND)
            return
        # Чекбокс "Удалять несовместимые моды"
        checkbox_delete_rect = pygame.Rect(70, 320, 20, 20)
        if checkbox_delete_rect.collidepoint(mx, my):
            pygame.mouse.set_cursor(CURSOR_HAND)
            return
        # Чекбокс "Скачивать стандартные моды"
        checkbox_download_rect = pygame.Rect(70, 360, 20, 20)
        if checkbox_download_rect.collidepoint(mx, my):
            pygame.mouse.set_cursor(CURSOR_HAND)
            return

    # Ползунок RAM
    slider_area = pygame.Rect(30, 80, 400, 60)
    if current_tab_index == 1 and slider_area.collidepoint(mx, my):
        pygame.mouse.set_cursor(CURSOR_HAND)
        return

    # Выпадающий список версий
    if show_dropdown:
        dropdown_bg = pygame.Rect(v_btn_rect.x, v_btn_rect.y - 255, v_btn_rect.width, 250)
        if dropdown_bg.collidepoint(mx, my):
            pygame.mouse.set_cursor(CURSOR_HAND)
            return

    # По умолчанию - обычная стрелка
    pygame.mouse.set_cursor(CURSOR_NORMAL)

# Создаём переключатель языка (в правом верхнем углу)
lang_switcher = LanguageSwitcher(WIDTH - 95, 15, 85, 32)

try:
    TOTAL_RAM = int(psutil.virtual_memory().total / (1024 ** 3))
except:
    TOTAL_RAM = 8

slider_x = 70 + (ram_gb - 1) * (400 // (TOTAL_RAM - 1 if TOTAL_RAM > 1 else 1))

CLR_BG, CLR_TOPBAR, CLR_PANEL = (15, 15, 18), (25, 25, 28), (35, 35, 38)
CLR_ACCENT, CLR_CANCEL = (60, 180, 60), (220, 60, 60)
CLR_SCROLL_BG, CLR_SCROLL_BAR = (40, 40, 45), (80, 80, 85)
WHITE, GRAY = (245, 245, 245), (140, 140, 145)

# Пути к файлам шрифтов
TITLE_FONT_PATH = "minecraft_title_cyrillic.ttf"
TEXT_FONT_PATH = "minecraft.ttf"

try:
    font_bold = pygame.font.Font(TITLE_FONT_PATH, 24)
    font_reg = pygame.font.Font(TEXT_FONT_PATH, 19)
    font_small = pygame.font.Font(TEXT_FONT_PATH, 16)
except FileNotFoundError as e:
    print(f" Не найден файл шрифта: {e}. Используются системные шрифты.")
    font_bold = pygame.font.SysFont("Segoe UI", 24, bold=True)
    font_reg = pygame.font.SysFont("Segoe UI", 19, bold=True)
    font_small = pygame.font.SysFont("Segoe UI", 16)

glow_alpha = 0.0
glow_speed = 0.05
button_hovered = False
button_idle_pulse = 0.0
button_idle_dir = 0.02
dropdown_anim = 0.0
dropdown_anim_speed = 0.1
dropdown_target = 0
spinner_angle = 0
spinner_active = False
progress = 0.0
progress_active = False

# Звёзды
stars = []
for _ in range(70):
    stars.append({
        'x': random.randint(0, WIDTH),
        'y': random.randint(0, HEIGHT),
        'speed': random.uniform(0.1, 0.8),
        'size': random.randint(1, 3),
        'twinkle': random.uniform(0.5, 1.5)
    })

scroll_velocity = 0
scroll_drag = 0.9
scroll_drag_offset = 0
hover_scale = 0.0
hover_speed = 0.1

tab_texts = [t("tab_play"), t("tab_settings")]
tab_text_surfs = [font_reg.render(text, True, WHITE) for text in tab_texts]
tab_text_widths = [s.get_width() for s in tab_text_surfs]

padding = 10
tab_bar_width = 90
tab_bar_height = 3
tab_bar_y = 46

tab_centers = [40 + i * 160 + 30 + w / 2 for i, w in enumerate(tab_text_widths)]
target_positions = [center - tab_bar_width / 2 for center in tab_centers]

current_tab_index = 0
current_tab = tab_texts[current_tab_index]
tab_bar_x = target_positions[current_tab_index]
target_tab_x = tab_bar_x
tab_animation_speed = 0.1

transition_active = False
transition_progress = 0.0
transition_direction = 1
from_tab_index = 0
to_tab_index = 0
transition_speed = 0.10

content_surface_play = pygame.Surface((860, 340), pygame.SRCALPHA)
content_surface_settings = pygame.Surface((860, 340), pygame.SRCALPHA)

def draw_play_tab(surface):
    surface.fill((0, 0, 0, 0))
    # Никнейм
    pygame.draw.rect(surface, CLR_PANEL, (0, 0, 240, 45), border_radius=8)
    if active_input:
        pygame.draw.rect(surface, CLR_ACCENT, (0, 0, 240, 45), 2, border_radius=8)
    blink = "|" if active_input and pygame.time.get_ticks() % 1000 < 500 else ""
    display_name = username if username else t("nickname_placeholder")
    surf_nick = font_small.render(display_name + blink, True, WHITE)
    surface.blit(surf_nick, (15, 12))
    surface.blit(font_small.render(t("nickname"), True, GRAY), (0, -25))

    # Основной блок
    pygame.draw.rect(surface, (30, 30, 33), (0, 60, 860, 280), border_radius=12)

    surface.blit(font_bold.render(f"Minecraft {all_versions[v_idx]}", True, WHITE), (30, 100))
    surface.blit(
        font_small.render(f"{t('loader')}: {loaders[l_idx]} | {t('ram')}: {ram_gb} {t('gb')}", True, CLR_ACCENT),
        (30, 150))
    surface.blit(font_small.render(f"{t('status')}: {status}", True, GRAY), (30, 300))

def draw_settings_tab(surface):
    surface.fill((0, 0, 0, 0))
    pygame.draw.rect(surface, (30, 30, 33), (0, 0, 860, 340), border_radius=12)

    surface.blit(font_reg.render(f"{t('ram')}: {ram_gb} {t('gb')}", True, WHITE), (30, 50))
    pygame.draw.rect(surface, CLR_PANEL, (30, 95, 400, 10), border_radius=5)
    pygame.draw.rect(surface, CLR_ACCENT, (30, 95, slider_x - 70, 10), border_radius=5)
    pygame.draw.rect(surface, WHITE, (slider_x - 50, 80, 24, 40), border_radius=6)

    surface.blit(font_small.render(f"{t('total_ram')}: {TOTAL_RAM} {t('gb')}", True, GRAY), (30, 140))

    # Fullscreen чекбокс
    pygame.draw.rect(surface, CLR_PANEL, (30, 190, 20, 20), border_radius=4)
    if fullscreen:
        pygame.draw.line(surface, CLR_ACCENT, (34, 200), (39, 205), 3)
        pygame.draw.line(surface, CLR_ACCENT, (39, 205), (46, 195), 3)
    surface.blit(font_small.render(t("fullscreen"), True, WHITE), (60, 190))

    # Чекбокс "Удалять несовместимые моды"
    y_offset = 230
    pygame.draw.rect(surface, CLR_PANEL, (30, y_offset, 20, 20), border_radius=4)
    if delete_incompatible_mods:
        pygame.draw.line(surface, CLR_ACCENT, (34, y_offset + 10), (39, y_offset + 15), 3)
        pygame.draw.line(surface, CLR_ACCENT, (39, y_offset + 15), (46, y_offset + 5), 3)
    surface.blit(font_small.render("Удалять несовместимые моды", True, WHITE), (60, y_offset))
    surface.blit(font_small.render("(проверка версии и очистка старых модов)", True, GRAY), (60, y_offset + 18))

    # Чекбокс "Скачивать стандартные моды (Fabric)"
    y_offset = 270
    pygame.draw.rect(surface, CLR_PANEL, (30, y_offset, 20, 20), border_radius=4)
    if download_standard_mods:
        pygame.draw.line(surface, CLR_ACCENT, (34, y_offset + 10), (39, y_offset + 15), 3)
        pygame.draw.line(surface, CLR_ACCENT, (39, y_offset + 15), (46, y_offset + 5), 3)
    surface.blit(font_small.render("Скачивать стандартные моды (Fabric)", True, WHITE), (60, y_offset))
    surface.blit(font_small.render("(Sodium, Iris, Fabric API)", True, GRAY), (60, y_offset + 18))

def extract_progress(status_text):
    match = re.search(r'(\d+(?:\.\d+)?)%', status_text)
    if match:
        return float(match.group(1)) / 100.0
    return None

clock = pygame.time.Clock()
running = True
scroll_target = None
scroll_speed = 0.1

while running:
    dt = clock.tick(144) / 16.67
    mx, my = pygame.mouse.get_pos()

    # ===== ОБНОВЛЯЕМ ВИД КУРСОРА =====
    update_cursor(mx, my)

    # Прямоугольники интерфейса
    play_rect = pygame.Rect(WIDTH // 2 - 110, 505, 220, 60)
    v_btn_rect = pygame.Rect(play_rect.x - 220, 505, 210, 60)
    l_rect = pygame.Rect(play_rect.right + 10, 505, 140, 60)
    nick_rect = pygame.Rect(40, 90, 240, 45)
    folder_rect = pygame.Rect(850, 512, 40, 40)
    dropdown_bg = pygame.Rect(v_btn_rect.x, v_btn_rect.y - 255, v_btn_rect.width, 250)
    checkbox_rect = pygame.Rect(70, 280, 20, 20)
    checkbox_delete_rect = pygame.Rect(70, 320, 20, 20)
    checkbox_download_rect = pygame.Rect(70, 360, 20, 20)

    # Скролл дропдауна
    visible_h = 248
    total_h = len(all_versions) * ITEM_H
    max_scroll = min(0, visible_h - total_h)
    sb_area = pygame.Rect(dropdown_bg.right - 16, dropdown_bg.y + 2, 14, dropdown_bg.height - 4)
    thumb_h = max(30, int((visible_h / (total_h if total_h > 0 else 1)) * sb_area.height))
    scroll_perc = scroll_y / max_scroll if max_scroll != 0 else 0
    thumb_rect = pygame.Rect(sb_area.x, sb_area.y + (scroll_perc * (sb_area.height - thumb_h)), 14, thumb_h)

    # Обработка перетаскивания ползунка
    if dragging_scroll:
        new_thumb_y = my - scroll_drag_offset
        new_thumb_y = max(sb_area.y, min(sb_area.y + sb_area.height - thumb_h, new_thumb_y))
        new_perc = (new_thumb_y - sb_area.y) / (sb_area.height - thumb_h)
        scroll_y = max_scroll * new_perc
        scroll_target = None
    else:
        if scroll_target is not None:
            scroll_y += (scroll_target - scroll_y) * scroll_speed * dt
            if abs(scroll_target - scroll_y) < 1:
                scroll_y = scroll_target
                scroll_target = None
        else:
            scroll_y += scroll_velocity
            scroll_velocity *= scroll_drag
            scroll_y = max(max_scroll, min(0, scroll_y))

    # Ползунок RAM
    if dragging_ram and current_tab_index == 1:
        slider_x = max(70, min(mx, 470))
        ram_gb = int(1 + (slider_x - 70) / (400 // (TOTAL_RAM - 1 if TOTAL_RAM > 1 else 1)))
        save_settings()

    # Анимация переключения вкладок
    if transition_active:
        transition_progress += transition_speed * dt
        if transition_progress >= 1.0:
            transition_progress = 1.0
            transition_active = False
            current_tab_index = to_tab_index
            current_tab = tab_texts[current_tab_index]

    if transition_active:
        start_x = target_positions[from_tab_index]
        end_x = target_positions[to_tab_index]
        tab_bar_x = start_x + (end_x - start_x) * transition_progress
    else:
        tab_bar_x = target_positions[current_tab_index]

    # Анимация дропдауна
    if show_dropdown:
        dropdown_target = 1
    else:
        dropdown_target = 0
    dropdown_anim += (dropdown_target - dropdown_anim) * 0.15 * dt
    dropdown_anim = max(0, min(1, dropdown_anim))

    # Пульсация кнопки
    if not is_running and not play_rect.collidepoint(mx, my) and not show_dropdown:
        button_idle_pulse += button_idle_dir * dt
        if button_idle_pulse > 1 or button_idle_pulse < 0:
            button_idle_dir *= -1
    else:
        button_idle_pulse = 0

    # Прогресс
    progress_val = extract_progress(status)
    progress_active = progress_val is not None
    if progress_active:
        progress = progress_val

    # Движение звёзд
    for star in stars:
        star['y'] += star['speed'] * dt
        if star['y'] > HEIGHT:
            star['y'] = 0
            star['x'] = random.randint(0, WIDTH)

    # Обновляем поверхности вкладок
    draw_play_tab(content_surface_play)
    draw_settings_tab(content_surface_settings)

    screen.fill(CLR_BG)

    # Звёзды
    for star in stars:
        twinkle = 0.7 + 0.3 * math.sin(pygame.time.get_ticks() * 0.002 + star['x'])
        color_val = int(150 * twinkle)
        color = (color_val, color_val, color_val)
        pygame.draw.circle(screen, color, (int(star['x']), int(star['y'])), star['size'])

    # Верхняя панель с вкладками
    pygame.draw.rect(screen, CLR_TOPBAR, (0, 0, WIDTH, 60))
    for i, tab in enumerate([t("tab_play"), t("tab_settings")]):
        tx = 40 + i * 160
        t_col = WHITE if (not transition_active and ((i == 0 and current_tab == t("tab_play")) or (
                    i == 1 and current_tab == t("tab_settings")))) or pygame.Rect(tx, 0, 150, 60).collidepoint(mx,
                                                                                                               my) else GRAY
        screen.blit(tab_text_surfs[i], (tx + 30, 18))

    # Полоска под вкладкой
    pygame.draw.rect(screen, CLR_ACCENT, (tab_bar_x, tab_bar_y, tab_bar_width, tab_bar_height), border_radius=2)

    # Рисуем переключатель языка
    lang_switcher.update(dt)
    lang_switcher.draw(screen)

    # Нижняя панель
    pygame.draw.rect(screen, (22, 22, 25), (0, 480, WIDTH, 120))

    # Кнопка ИГРАТЬ/ОТМЕНА
    if play_rect.collidepoint(mx, my):
        hover_scale = min(1.0, hover_scale + hover_speed * dt)
    else:
        hover_scale = max(0.0, hover_scale - hover_speed * dt)

    if is_running:
        base_color = CLR_CANCEL
    else:
        base_color = CLR_ACCENT

    scale = 1.0 + 0.02 * button_idle_pulse + 0.08 * hover_scale
    scaled_rect = pygame.Rect(0, 0, int(play_rect.w * scale), int(play_rect.h * scale))
    scaled_rect.center = play_rect.center
    pygame.draw.rect(screen, base_color, scaled_rect, border_radius=10)
    btn_text = t("cancel") if is_running else t("play")
    btn_surf = font_bold.render(btn_text, True, WHITE)
    screen.blit(btn_surf, (scaled_rect.centerx - btn_surf.get_width() // 2,
                           scaled_rect.centery - btn_surf.get_height() // 2))

    # Прогресс-бар
    if progress_active:
        bar_y = 478
        bar_height = 4
        bar_width = int(WIDTH * progress)
        pygame.draw.rect(screen, CLR_PANEL, (0, bar_y, WIDTH, bar_height))
        pygame.draw.rect(screen, CLR_ACCENT, (0, bar_y, bar_width, bar_height))

    # Кнопка выбора версии
    pygame.draw.rect(screen, CLR_PANEL, v_btn_rect, border_radius=10)
    screen.blit(font_small.render(all_versions[v_idx][:18], True, WHITE), (v_btn_rect.x + 15, 523))

    # Кнопка выбора ядра
    pygame.draw.rect(screen, CLR_PANEL, l_rect, border_radius=10)
    l_txt = loaders[l_idx]
    screen.blit(font_small.render(l_txt, True, WHITE), (l_rect.centerx - font_small.size(l_txt)[0] // 2, 523))

    # Кнопка-папка
    pygame.draw.rect(screen, CLR_PANEL, folder_rect, border_radius=6)
    body_rect = pygame.Rect(folder_rect.x + 4, folder_rect.y + 6, folder_rect.w - 2, folder_rect.h - 10)
    pygame.draw.rect(screen, WHITE, body_rect, border_radius=3)
    handle_rect = pygame.Rect(folder_rect.x + 18, folder_rect.y + 2, 22, 5)
    pygame.draw.rect(screen, WHITE, handle_rect, border_radius=2)

    # Отрисовка содержимого вкладок
    if transition_active:
        offset_from = -transition_direction * (transition_progress * WIDTH)
        offset_to = transition_direction * ((1 - transition_progress) * WIDTH)
        if from_tab_index == 0:
            screen.blit(content_surface_play, (40 + offset_from, 90))
        else:
            screen.blit(content_surface_settings, (40 + offset_from, 90))
        if to_tab_index == 0:
            screen.blit(content_surface_play, (40 + offset_to, 90))
        else:
            screen.blit(content_surface_settings, (40 + offset_to, 90))
    else:
        if current_tab_index == 0:
            screen.blit(content_surface_play, (40, 90))
        else:
            screen.blit(content_surface_settings, (40, 90))

    # Подписи под кнопками
    screen.blit(font_small.render(t("version"), True, GRAY), (v_btn_rect.x, 485))
    screen.blit(font_small.render(t("loader"), True, GRAY), (l_rect.x, 485))

    # Анимированный дропдаун
    if dropdown_anim > 0:
        t_anim = dropdown_anim
        eased_t = 1 - (1 - t_anim) ** 2
        scale_drop = 0.8 + 0.2 * eased_t
        alpha = int(255 * t_anim)

        dropdown_surf = pygame.Surface((dropdown_bg.width, dropdown_bg.height), pygame.SRCALPHA)
        pygame.draw.rect(dropdown_surf, CLR_PANEL, (0, 0, dropdown_bg.width, dropdown_bg.height), border_radius=12)
        old_clip = dropdown_surf.get_clip()
        dropdown_surf.set_clip(pygame.Rect(0, 0, dropdown_bg.width - 18, dropdown_bg.height))
        for i, v_name in enumerate(all_versions):
            iy = 5 + (i * ITEM_H) + scroll_y
            item_r = pygame.Rect(5, iy, dropdown_bg.width - 25, ITEM_H - 4)
            if 0 - ITEM_H < iy < dropdown_bg.height:
                global_item_rect = pygame.Rect(dropdown_bg.x + 5, dropdown_bg.y + iy,
                                               dropdown_bg.width - 25, ITEM_H - 4)
                bg_c = (65, 65, 70) if global_item_rect.collidepoint(mx, my) else (45, 45, 48)
                pygame.draw.rect(dropdown_surf, bg_c, item_r, border_radius=6)
                text_surf = font_small.render(v_name, True, WHITE)
                dropdown_surf.blit(text_surf, (item_r.x + 12, item_r.y + 8))
        dropdown_surf.set_clip(old_clip)
        sb_local = pygame.Rect(dropdown_bg.width - 14, 2, 14, dropdown_bg.height - 4)
        pygame.draw.rect(dropdown_surf, CLR_SCROLL_BG, sb_local, border_radius=4)
        thumb_local_h = thumb_h
        thumb_local_y = 2 + (scroll_perc * (sb_local.height - thumb_local_h))
        pygame.draw.rect(dropdown_surf, CLR_SCROLL_BAR,
                         (sb_local.x, thumb_local_y, 14, thumb_local_h), border_radius=4)

        scaled_dropdown = pygame.transform.smoothscale(dropdown_surf,
                                                       (int(dropdown_bg.width * scale_drop),
                                                        int(dropdown_bg.height * scale_drop)))
        scaled_dropdown.set_alpha(alpha)
        blit_x = dropdown_bg.centerx - scaled_dropdown.get_width() // 2
        blit_y = dropdown_bg.centery - scaled_dropdown.get_height() // 2
        screen.blit(scaled_dropdown, (blit_x, blit_y))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_settings()
            stop_discord_presence()
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEWHEEL:
            if show_dropdown:
                scroll_velocity += event.y * 20

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Переключатель языка
            new_lang = lang_switcher.handle_event(event)
            if new_lang and new_lang != current_lang:
                current_lang = new_lang
                save_settings()
                # Обновляем текст вкладок
                tab_text_surfs = [font_reg.render(t("tab_play"), True, WHITE),
                                  font_reg.render(t("tab_settings"), True, WHITE)]
                tab_text_widths = [s.get_width() for s in tab_text_surfs]
                tab_centers = [40 + i * 160 + 30 + w / 2 for i, w in enumerate(tab_text_widths)]
                target_positions = [center - tab_bar_width / 2 for center in tab_centers]
                continue

            # Дропдаун
            if show_dropdown and dropdown_bg.collidepoint(event.pos):
                if sb_area.collidepoint(event.pos):
                    if thumb_rect.collidepoint(event.pos):
                        dragging_scroll = True
                        scroll_drag_offset = my - thumb_rect.y
                        scroll_target = None
                    else:
                        new_thumb_center_y = max(sb_area.y + thumb_h // 2, min(my, sb_area.bottom - thumb_h // 2))
                        new_perc = (new_thumb_center_y - sb_area.y - thumb_h / 2) / (sb_area.height - thumb_h)
                        scroll_target = max_scroll * new_perc
                else:
                    rel_y = event.pos[1] - dropdown_bg.y - 5 - scroll_y
                    idx = int(rel_y // ITEM_H)
                    if 0 <= idx < len(all_versions):
                        v_idx = idx
                        show_dropdown = False
                        save_settings()
                continue

            if show_dropdown and not v_btn_rect.collidepoint(event.pos):
                show_dropdown = False

            # Вкладки
            if pygame.Rect(40, 0, 150, 60).collidepoint(event.pos) and not transition_active:
                if current_tab_index != 0:
                    from_tab_index = current_tab_index
                    to_tab_index = 0
                    transition_direction = 1 if to_tab_index > from_tab_index else -1
                    transition_active = True
                    transition_progress = 0.0
                show_dropdown = False
                continue

            if pygame.Rect(200, 0, 150, 60).collidepoint(event.pos) and not transition_active:
                if current_tab_index != 1:
                    from_tab_index = current_tab_index
                    to_tab_index = 1
                    transition_direction = 1 if to_tab_index > from_tab_index else -1
                    transition_active = True
                    transition_progress = 0.0
                show_dropdown = False
                continue

            # Кнопка ИГРАТЬ/ОТМЕНА
            if play_rect.collidepoint(event.pos):
                if is_running:
                    cancel_requested = True
                    if installer_process:
                        installer_process.terminate()
                    if minecraft_process:
                        minecraft_process.terminate()
                    status = t("cancelling")
                else:
                    threading.Thread(target=run_launch_logic, daemon=True).start()
                continue

            # Кнопка выбора версии
            if v_btn_rect.collidepoint(event.pos):
                show_dropdown = not show_dropdown
                if not show_dropdown:
                    dropdown_anim = 0
                continue

            # Кнопка выбора ядра
            if l_rect.collidepoint(event.pos):
                l_idx = (l_idx + 1) % len(loaders)
                save_settings()
                continue

            # Кнопка-папка
            if folder_rect.collidepoint(event.pos):
                os.startfile(GAME_DIR)
                continue

            # Поле ввода ника
            if not transition_active and current_tab_index == 0:
                if nick_rect.collidepoint(event.pos):
                    active_input = True
                else:
                    active_input = False

            # Настройки
            if not transition_active and current_tab_index == 1:
                if checkbox_rect.collidepoint(event.pos):
                    fullscreen = not fullscreen
                    save_settings()
                if checkbox_delete_rect.collidepoint(event.pos):
                    delete_incompatible_mods = not delete_incompatible_mods
                    save_settings()
                if checkbox_download_rect.collidepoint(event.pos):
                    download_standard_mods = not download_standard_mods
                    save_settings()
                if pygame.Rect(70, 185, 400, 40).collidepoint(event.pos):
                    dragging_ram = True

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                dragging_ram = dragging_scroll = False
                save_settings()

        if event.type == pygame.KEYDOWN and active_input and not transition_active and current_tab_index == 0:
            if event.key == pygame.K_BACKSPACE:
                username = username[:-1]
            elif event.key == pygame.K_RETURN:
                active_input = False
            else:
                if len(username) < 16 and event.unicode.isprintable():
                    username += event.unicode
            save_settings()

    pygame.display.flip()
    clock.tick(120)
