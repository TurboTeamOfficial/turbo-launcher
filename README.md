<div align="center">

# 🚀 Turbo Launcher

### Современный лаунчер для Minecraft с душой

[![Version](https://img.shields.io/badge/version-1.0.0-brightgreen.svg)](https://github.com/TT/turbo-launcher/releases)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-GPLv3-red.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/TT/turbo-launcher)
[![Discord](https://img.shields.io/badge/chat-discord-7289da.svg)](https://discord.gg/your-server)

![Turbo Launcher Banner](https://i.postimg.cc/TP0wZMDy/Turbo-Launcher-Preview.png)

</div>

---

## ✨ Особенности

<div align="center">

| 🎮 Игровые | ⚙️ Технические | 💬 Социальные |
|------------|----------------|---------------|
| Все версии Minecraft | Автоустановка Java | Discord Rich Presence |
| Fabric / Forge / Vanilla | Портативный режим | Онлайн-счётчик |
| Автоустановка модов | Умный выбор зеркал | Discord бот команды |
| Оптимизация FPS | Работа без интернета | Ely.by авторизация |

</div>

---

## 🎯 Что умеет лаунчер?

- ✅ **Поддержка 50+ версий** Minecraft (от 1.7.10 до 1.21+)
- ✅ **Автоматическая установка** Fabric, Forge
- ✅ **Умный установщик модов** (Sodium, Iris, Fabric API)
- ✅ **Встроенная Java** — качает нужную версию автоматически
- ✅ **Русский/English интерфейс**
- ✅ **Discord статус** — друзья видят, во что вы играете
- ✅ **Кроссплатформенность** — Windows, Linux, macOS
- ✅ **Никаких скрытых сборов** — полностью бесплатно

---

## 📸 Скриншоты

<div align="center">
  
| Главное окно | Настройки | Выбор версий |
|--------------|-----------|--------------|
| ![Main](https://via.placeholder.com/300x200?text=Main+Window) | ![Settings](https://via.placeholder.com/300x200?text=Settings) | ![Versions](https://via.placeholder.com/300x200?text=Versions) |

</div>

---

## 📋 Системные требования

### Минимальные:
| Компонент | Требование |
|-----------|-------------|
| **Операционная система** | Windows 10 / Linux / macOS |
| **Оперативная память** | 2 ГБ |
| **Свободное место на диске** | 500 МБ |
| **Интернет** | Только для первого запуска |

### Рекомендуемые:
| Компонент | Требование |
|-----------|-------------|
| **Операционная система** | Windows 11 |
| **Оперативная память** | 8 ГБ+ |
| **Свободное место на диске** | 5+ ГБ |
| **Процессор** | 4+ ядра |
| **Интернет** | Стабильное соединение |

---

## 🚀 Быстрый старт

### Для игроков (самый простой способ)

1. 📥 **Скачайте** последнюю версию из [Releases](https://github.com/TT/turbo-launcher/releases)
2. 📂 **Распакуйте** в любую папку (например, `C:\Games\TurboLauncher`)
3. 🖱️ **Запустите** `TurboLauncher.exe`
4. 🎮 **Выберите** версию и нажмите "ИГРАТЬ"

> 💡 **Совет:** Лаунчер портативный — можно носить на флешке!

### Для разработчиков

```bash
# Клонируем репозиторий
git clone https://github.com/TT/turbo-launcher.git
cd turbo-launcher

# Создаём виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Устанавливаем зависимости
pip install -r requirements.txt

# Запускаем
python launcher.py
