import os
import sys
import json
import requests
import shutil
import subprocess
import pygame
import threading
import time
import ctypes
from ctypes import wintypes

# ==========================================================
# НАСТРОЙКИ
# ==========================================================
FILES_LIST_URL = "https://gitflic.ru/project/turboteam/turbo-launcher/blob/raw?file=files.json"
CURRENT_DIR = os.path.dirname(sys.executable)
VERSION_FILE = os.path.join(CURRENT_DIR, "version.txt")

# Папки и файлы, которые НЕЛЬЗЯ удалять (игра, настройки, сам апдейтер)
KEEP = {
    ".turbo_launcher",   # Вся игра, моды, Java, настройки
    "updater.exe",       # Сам апдейтер
    "runtime",           # Java (если вдруг в папке лаунчера)
    "versions",          # Версии Minecraft
    "mods",              # Моды
    "assets",            # Ресурсы игры
    "libraries",         # Библиотеки
    "logs",              # Логи (не критично, но лучше не трогать)
}

# Цвета
BG_COLOR = (15, 15, 18)
TEXT_COLOR = (255, 255, 255)
ACCENT_COLOR = (60, 180, 60)
ERROR_COLOR = (220, 60, 60)

WIDTH, HEIGHT = 420, 320

def round_corners(hwnd, radius=30):
    try:
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        hRgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, width, height, radius, radius)
        ctypes.windll.user32.SetWindowRgn(hwnd, hRgn, True)
        return True
    except:
        return False

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("Turbo Launcher - Updater")
hwnd = pygame.display.get_wm_info()["window"]
round_corners(hwnd, 30)

try:
    avatar = pygame.image.load("turbolauncher.ico")
    avatar = pygame.transform.scale(avatar, (80, 80))
except:
    avatar = pygame.Surface((80, 80))
    avatar.fill(ACCENT_COLOR)

try:
    font = pygame.font.Font("minecraft.ttf", 16)
    font_small = pygame.font.Font("minecraft.ttf", 12)
except:
    font = pygame.font.SysFont("Segoe UI", 16)
    font_small = pygame.font.SysFont("Segoe UI", 12)

def get_file_list():
    try:
        resp = requests.get(FILES_LIST_URL, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def download_file(url, dest_path):
    try:
        r = requests.get(url, stream=True, timeout=60)
        if r.status_code == 200:
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            return True
    except:
        pass
    return False

def launch_launcher():
    launcher_path = os.path.join(CURRENT_DIR, "Turbo Launcher.exe")
    if os.path.exists(launcher_path):
        subprocess.Popen([launcher_path])
    sys.exit(0)

# === Проверка версии ===
data = get_file_list()
if not data:
    screen.fill(BG_COLOR)
    avatar_rect = avatar.get_rect(center=(WIDTH//2, HEIGHT//2 - 40))
    screen.blit(avatar, avatar_rect)
    error_text = font.render("Ошибка подключения", True, ERROR_COLOR)
    screen.blit(error_text, error_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 20)))
    error_text2 = font_small.render("Не удалось получить список файлов", True, TEXT_COLOR)
    screen.blit(error_text2, error_text2.get_rect(center=(WIDTH//2, HEIGHT//2 + 50)))
    error_text3 = font_small.render("Программа закроется через 3 секунды...", True, TEXT_COLOR)
    screen.blit(error_text3, error_text3.get_rect(center=(WIDTH//2, HEIGHT//2 + 80)))
    pygame.display.flip()
    time.sleep(3)
    pygame.quit()
    sys.exit(1)

server_version = data.get("version", "")
local_version = ""
if os.path.exists(VERSION_FILE):
    with open(VERSION_FILE, "r") as f:
        local_version = f.read().strip()

if local_version == server_version:
    launch_launcher()

# === Обновление ===
status_text = "Обновление Turbo Launcher..."
error_message = ""
update_done = False

def update_worker():
    global status_text, error_message, update_done

    # Удаляем ТОЛЬКО файлы лаунчера, НЕ ТРОГАЕМ игру и важные папки
    for item in os.listdir(CURRENT_DIR):
        if item in KEEP:
            continue
        path = os.path.join(CURRENT_DIR, item)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except:
            pass

    # Скачиваем новые файлы
    for file_info in data["files"]:
        name = file_info["name"]
        url = file_info["url"]
        dest = os.path.join(CURRENT_DIR, name)
        if not download_file(url, dest):
            error_message = f"Ошибка: {name}"
            return

    # Обновляем версию
    with open(VERSION_FILE, "w") as f:
        f.write(server_version)

    status_text = "Запуск Turbo Launcher..."
    time.sleep(1)
    update_done = True

threading.Thread(target=update_worker, daemon=True).start()

clock = pygame.time.Clock()
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            running = False

    screen.fill(BG_COLOR)

    avatar_rect = avatar.get_rect(center=(WIDTH//2, HEIGHT//2 - 40))
    screen.blit(avatar, avatar_rect)

    if error_message:
        text_color = ERROR_COLOR
        display_text = error_message
    else:
        text_color = ACCENT_COLOR if update_done else TEXT_COLOR
        display_text = status_text

    text_surf = font.render(display_text, True, text_color)
    screen.blit(text_surf, text_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 40)))

    pygame.display.flip()
    clock.tick(60)

    if update_done:
        launch_launcher()

pygame.quit()
sys.exit()
