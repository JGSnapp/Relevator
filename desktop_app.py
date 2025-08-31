import tkinter as tk
import customtkinter as ctk
import threading
import time
import base64
import io
import requests
import pyautogui
import keyboard
import mouse
from PIL import Image, ImageTk
import json
import os
from dotenv import load_dotenv
import datetime
import cv2
import numpy as np

# Настройка customtkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class RelevatorPanel:
    # Константы настройки
    SAVE_SCREENSHOTS = True  # Сохранять ли скриншоты в файлы (True/False)
    SIMILARITY_THRESHOLD = 0.85  # Порог схожести (0.85 = 85% схожести)
    ENABLE_SIMILARITY_CHECK = True  # Включить проверку схожести скриншотов
    
    def __init__(self):
        # Загрузка переменных окружения
        load_dotenv()
        
        self.root = ctk.CTk()
        self.root.title("Relevator")
        self.root.geometry("320x600")
        
        # Полупрозрачное окно
        self.root.attributes('-alpha', 0.95)
        
        # Поверх всех окон
        self.root.attributes('-topmost', True)
        
        # Убираем стандартную рамку окна
        self.root.overrideredirect(True)
        
        # Позиционируем в правом верхнем углу
        self.position_window()
    
    def position_window(self):
        """Позиционирование окна в правом верхнем углу экрана"""
        # Получаем размеры экрана
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Размеры окна
        window_width = 320
        window_height = 600
        
        # Вычисляем позицию (правый верхний угол с небольшим отступом)
        x = screen_width - window_width - 20
        y = 20
        
        # Устанавливаем позицию
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Переменные состояния
        self.is_capturing = False
        self.last_activity = time.time()
        self.capture_thread = None
        self.server_url = os.getenv("SERVER_URL", "http://localhost:8000")
        self.screenshots_buffer = []  # Буфер для накопления скриншотов
        self.capture_interval = 1.5  # Интервал захвата в секундах
        self.inactivity_threshold = 1.5  # Порог неактивности в секундах
        
        # Система папок для скриншотов
        self.screenshots_dir = "screenshots"
        self.current_session_dir = None
        
        # Проверяем настройку сохранения скриншотов из переменных окружения
        save_screenshots_env = os.getenv("SAVE_SCREENSHOTS", "True").lower()
        if save_screenshots_env in ["false", "0", "no", "off"]:
            self.SAVE_SCREENSHOTS = False
        
        # Проверяем настройки фильтрации из переменных окружения
        similarity_check_env = os.getenv("ENABLE_SIMILARITY_CHECK", "True").lower()
        if similarity_check_env in ["false", "0", "no", "off"]:
            self.ENABLE_SIMILARITY_CHECK = False
        
        similarity_threshold_env = os.getenv("SIMILARITY_THRESHOLD", "0.85")
        try:
            self.SIMILARITY_THRESHOLD = float(similarity_threshold_env)
        except ValueError:
            self.SIMILARITY_THRESHOLD = 0.85
        
        # Создаем основную папку для скриншотов только если включено сохранение
        if self.SAVE_SCREENSHOTS and not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)
        
        self.setup_ui()
        self.setup_hotkeys()
        
    def setup_ui(self):
        # Создаем кастомную заголовочную панель
        self.create_title_bar()
        
        # Основной контейнер
        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # Панель управления
        control_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Статус и счетчик
        status_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ctk.CTkLabel(status_frame, text="Ожидание...", 
                                        font=ctk.CTkFont(size=12))
        self.status_label.pack(side=tk.LEFT)
        
        self.counter_label = ctk.CTkLabel(status_frame, text="Скриншотов: 0", 
                                         font=ctk.CTkFont(size=12))
        self.counter_label.pack(side=tk.RIGHT)
        
        # Кнопки управления
        buttons_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        buttons_frame.pack(fill=tk.X)
        
        # Кнопка запуска/остановки
        self.toggle_button = ctk.CTkButton(buttons_frame, text="Запустить захват", 
                                          command=self.toggle_capture,
                                          font=ctk.CTkFont(size=14, weight="bold"),
                                          height=35,
                                          corner_radius=8)
        self.toggle_button.pack(fill=tk.X)
        
        # Область для подсказок
        suggestions_container = ctk.CTkFrame(main_container, fg_color="transparent")
        suggestions_container.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок подсказок
        suggestions_header = ctk.CTkLabel(suggestions_container, text="Подсказки", 
                                         font=ctk.CTkFont(size=16, weight="bold"))
        suggestions_header.pack(anchor=tk.W, pady=(0, 10))
        
        # Контейнер для блоков подсказок с прокруткой
        self.suggestions_scrollable_frame = ctk.CTkScrollableFrame(suggestions_container, 
                                                                  fg_color="transparent")
        self.suggestions_scrollable_frame.pack(fill=tk.BOTH, expand=True)
        
        # Настройка тегов для HTML форматирования
        self.setup_text_tags()
    

    
    def create_title_bar(self):
        """Создание кастомной заголовочной панели"""
        title_bar = ctk.CTkFrame(self.root, height=35, fg_color=("#2b2b2b", "#1a1a1a"))
        title_bar.pack(fill=tk.X)
        title_bar.pack_propagate(False)
        
        # Заголовок окна
        title_label = ctk.CTkLabel(title_bar, text="Relevator", 
                                  font=ctk.CTkFont(size=14, weight="bold"))
        title_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Кнопки управления окном
        button_frame = ctk.CTkFrame(title_bar, fg_color="transparent")
        button_frame.pack(side=tk.RIGHT, padx=5)
        
        # Кнопка сворачивания
        minimize_button = ctk.CTkButton(button_frame, text="−", 
                                       command=self.root.iconify,
                                       width=25, height=25,
                                       font=ctk.CTkFont(size=16, weight="bold"),
                                       corner_radius=4)
        minimize_button.pack(side=tk.LEFT, padx=2)
        
        # Кнопка закрытия
        close_button = ctk.CTkButton(button_frame, text="×", 
                                    command=self.root.quit,
                                    width=25, height=25,
                                    font=ctk.CTkFont(size=16, weight="bold"),
                                    corner_radius=4,
                                    fg_color=("#ff4444", "#cc3333"),
                                    hover_color=("#ff6666", "#dd4444"))
        close_button.pack(side=tk.LEFT, padx=2)
        
        # Возможность перетаскивания окна
        title_bar.bind('<Button-1>', self.start_move)
        title_bar.bind('<B1-Motion>', self.on_move)
        title_label.bind('<Button-1>', self.start_move)
        title_label.bind('<B1-Motion>', self.on_move)
    
    def start_move(self, event):
        """Начало перетаскивания окна"""
        self.x = event.x
        self.y = event.y
    
    def on_move(self, event):
        """Перетаскивание окна"""
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")
    
    def setup_text_tags(self):
        """Настройка тегов для форматирования текста"""
        self.text_tags = {
            "title": {"foreground": "#4CAF50", "font": ('Segoe UI', 12, 'bold')},
            "subtitle": {"foreground": "#2196F3", "font": ('Segoe UI', 10, 'bold')},
            "important": {"foreground": "#FF9800", "font": ('Segoe UI', 10, 'bold')},
            "code": {"foreground": "#E91E63", "font": ('Consolas', 9)},
            "emphasis": {"foreground": "#9C27B0", "font": ('Segoe UI', 10, 'italic')}
        }
        
    def setup_hotkeys(self):
        # Глобальные хоткеи для отслеживания активности
        keyboard.on_press(self.on_key_press)
        mouse.on_click(self.on_mouse_click)
        
    def on_key_press(self, event=None):
        self.last_activity = time.time()
        
    def on_mouse_click(self, event=None):
        self.last_activity = time.time()
        
    def toggle_capture(self):
        if not self.is_capturing:
            self.start_capture()
        else:
            self.stop_capture()
    
    def manual_analysis(self):
        """Ручной анализ накопленных скриншотов"""
        if self.screenshots_buffer:
            self.process_accumulated_screenshots()
        else:
            self.status_label.configure(text="Нет скриншотов для анализа")
            
    def start_capture(self):
        self.is_capturing = True
        self.toggle_button.configure(text="Остановить захват", 
                                   fg_color=("#ff4444", "#cc3333"),
                                   hover_color=("#ff6666", "#dd4444"))
        self.status_label.configure(text="Захват активен...")
        
        # Запуск потока захвата
        self.capture_thread = threading.Thread(target=self.capture_loop, daemon=True)
        self.capture_thread.start()
        
    def stop_capture(self):
        self.is_capturing = False
        self.toggle_button.configure(text="Запустить захват", 
                                   fg_color=("#2b2b2b", "#1a1a1a"),
                                   hover_color=("#3b3b3b", "#2a2a2a"))
        self.status_label.configure(text="Ожидание...")
        
    def capture_loop(self):
        last_capture_time = 0
        
        while self.is_capturing:
            try:
                current_time = time.time()
                time_since_activity = current_time - self.last_activity
                time_since_last_capture = current_time - last_capture_time
                
                # Если пользователь активен и прошло достаточно времени с последнего захвата
                if time_since_activity < self.inactivity_threshold and time_since_last_capture >= self.capture_interval:
                    self.capture_screenshot()
                    last_capture_time = current_time
                
                # Если пользователь неактивен и есть накопленные скриншоты
                elif time_since_activity >= self.inactivity_threshold and self.screenshots_buffer:
                    self.process_accumulated_screenshots()
                    last_capture_time = current_time
                
                time.sleep(0.1)  # Короткая пауза для проверки
                
            except Exception as e:
                print(f"Ошибка в цикле захвата: {e}")
                time.sleep(1)
                
    def create_new_session(self):
        """Создание новой папки для сессии записи"""
        if not self.SAVE_SCREENSHOTS:
            return
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session_dir = os.path.join(self.screenshots_dir, f"session_{timestamp}")
        
        if not os.path.exists(self.current_session_dir):
            os.makedirs(self.current_session_dir)
            
        print(f"Создана новая сессия: {self.current_session_dir}")
    
    def compare_images(self, img1_data, img2_data):
        """Сравнение двух изображений в формате base64"""
        try:
            # Декодируем base64 в numpy массивы
            img1_bytes = base64.b64decode(img1_data)
            img1_np = np.frombuffer(img1_bytes, np.uint8)
            img1_cv = cv2.imdecode(img1_np, cv2.IMREAD_COLOR)
            
            img2_bytes = base64.b64decode(img2_data)
            img2_np = np.frombuffer(img2_bytes, np.uint8)
            img2_cv = cv2.imdecode(img2_np, cv2.IMREAD_COLOR)
            
            # Приводим к одинаковому размеру
            height, width = img1_cv.shape[:2]
            img2_cv = cv2.resize(img2_cv, (width, height))
            
            # Вычисляем структурное сходство (SSIM)
            # Конвертируем в оттенки серого для лучшего сравнения
            gray1 = cv2.cvtColor(img1_cv, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2_cv, cv2.COLOR_BGR2GRAY)
            
            # Вычисляем корреляцию
            correlation = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)
            similarity = correlation[0][0]
            
            return similarity
            
        except Exception as e:
            print(f"Ошибка сравнения изображений: {e}")
            return 0.0
    
    def filter_similar_screenshots(self, screenshots):
        """Фильтрация похожих скриншотов"""
        if not self.ENABLE_SIMILARITY_CHECK or len(screenshots) <= 1:
            # Возвращаем все скриншоты как принятые
            return screenshots, [True] * len(screenshots)
        
        filtered = [screenshots[0]]  # Первый скриншот всегда добавляем
        accepted_indices = [0]  # Индексы принятых скриншотов
        
        for i in range(1, len(screenshots)):
            current_screenshot = screenshots[i]
            is_similar = False
            
            # Сравниваем с последними несколькими скриншотами
            for j in range(max(0, len(filtered) - 2), len(filtered)):
                similarity = self.compare_images(current_screenshot, filtered[j])
                if similarity >= self.SIMILARITY_THRESHOLD:
                    is_similar = True
                    print(f"Скриншот {i+1} похож на {j+1} (схожесть: {similarity:.2f})")
                    break
            
            if not is_similar:
                filtered.append(current_screenshot)
                accepted_indices.append(i)
                print(f"Добавлен уникальный скриншот {i+1}")
        
        # Создаем список статусов для всех скриншотов
        status_list = [False] * len(screenshots)
        for idx in accepted_indices:
            status_list[idx] = True
        
        print(f"Отфильтровано: {len(screenshots)} -> {len(filtered)} скриншотов")
        return filtered, status_list
    

    
    def capture_screenshot(self):
        """Захват одного скриншота и добавление в буфер"""
        try:
            self.status_label.configure(text="Захват скриншота...")
            
            # Захват скриншота
            screenshot = pyautogui.screenshot()
            
            # Конвертация в base64
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            image_data = base64.b64encode(buffer.getvalue()).decode()
            
            # Добавление в буфер
            self.screenshots_buffer.append(image_data)
            self.counter_label.configure(text=f"Скриншотов: {len(self.screenshots_buffer)}")
            self.status_label.configure(text=f"Скриншот добавлен в буфер ({len(self.screenshots_buffer)})")
            
        except Exception as e:
            print(f"Ошибка захвата скриншота: {e}")
            self.status_label.configure(text="Ошибка захвата")
    
    def process_accumulated_screenshots(self):
        """Обработка всех накопленных скриншотов"""
        try:
            if not self.screenshots_buffer:
                return
                
            # Фильтруем похожие скриншоты
            filtered_screenshots, status_list = self.filter_similar_screenshots(self.screenshots_buffer)
            
            # Создаем новую папку для сессии при отправке скриншотов
            self.create_new_session()
            
            # Сохраняем все скриншоты с пометками о статусе
            for i, image_data in enumerate(self.screenshots_buffer):
                # Декодируем base64 обратно в изображение
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
                
                # Определяем статус скриншота
                is_accepted = status_list[i]
                status_mark = "ACCEPTED" if is_accepted else "FILTERED"
                
                # Сохраняем в файл с пометкой статуса
                filename = f"screenshot_{i+1:03d}_{status_mark}.png"
                filepath = os.path.join(self.current_session_dir, filename)
                image.save(filepath)
                print(f"Сохранен скриншот: {filepath}")
                
            self.status_label.configure(text=f"Отправка {len(filtered_screenshots)} скриншотов...")
            
            # Отправка отфильтрованных скриншотов на сервер
            response = requests.post(
                f"{self.server_url}/process-screenshots",
                json={"screenshots": filtered_screenshots},
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                suggestions = result.get("suggestions", [])
                self.display_suggestions(suggestions)
                self.status_label.configure(text=f"Обработано {len(filtered_screenshots)} из {len(self.screenshots_buffer)} скриншотов")
                # Очищаем буфер после успешной обработки
                self.screenshots_buffer.clear()
                self.counter_label.configure(text="Скриншотов: 0")
            else:
                self.status_label.configure(text=f"Ошибка сервера: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.status_label.configure(text="Ошибка соединения с сервером")
            print(f"Ошибка запроса: {e}")
        except Exception as e:
            self.status_label.configure(text="Ошибка обработки")
            print(f"Ошибка: {e}")
            
    def parse_html_content(self, html_content):
        """Парсинг HTML контента и применение форматирования"""
        # Простой парсер HTML тегов
        content = html_content
        
        # Заменяем HTML теги на специальные маркеры
        content = content.replace('<h3>', '§SUBTITLE§')
        content = content.replace('</h3>', '§/SUBTITLE§')
        content = content.replace('<strong>', '§IMPORTANT§')
        content = content.replace('</strong>', '§/IMPORTANT§')
        content = content.replace('<em>', '§EMPHASIS§')
        content = content.replace('</em>', '§/EMPHASIS§')
        content = content.replace('<code>', '§CODE§')
        content = content.replace('</code>', '§/CODE§')
        content = content.replace('<br>', '\n')
        content = content.replace('<ul>', '\n')
        content = content.replace('</ul>', '\n')
        content = content.replace('<li>', '• ')
        content = content.replace('</li>', '\n')
        
        return content
    
    def insert_formatted_text(self, text):
        """Вставка текста с форматированием"""
        current_pos = 0
        
        while current_pos < len(text):
            # Ищем маркеры форматирования
            subtitle_start = text.find('§SUBTITLE§', current_pos)
            important_start = text.find('§IMPORTANT§', current_pos)
            emphasis_start = text.find('§EMPHASIS§', current_pos)
            code_start = text.find('§CODE§', current_pos)
            
            # Находим ближайший маркер
            markers = [(subtitle_start, 'subtitle'), (important_start, 'important'), 
                      (emphasis_start, 'emphasis'), (code_start, 'code')]
            markers = [(pos, tag) for pos, tag in markers if pos != -1]
            
            if not markers:
                # Вставляем оставшийся текст без форматирования
                remaining_text = text[current_pos:]
                if remaining_text:
                    self.suggestions_text.insert(tk.END, remaining_text)
                break
            
            # Сортируем по позиции
            markers.sort(key=lambda x: x[0])
            next_marker_pos, next_marker_tag = markers[0]
            
            # Вставляем текст до маркера
            if next_marker_pos > current_pos:
                plain_text = text[current_pos:next_marker_pos]
                self.suggestions_text.insert(tk.END, plain_text)
            
            # Обрабатываем маркер
            if next_marker_tag == 'subtitle':
                end_pos = text.find('§/SUBTITLE§', next_marker_pos)
                if end_pos != -1:
                    subtitle_text = text[next_marker_pos + 11:end_pos]
                    self.suggestions_text.insert(tk.END, subtitle_text, "subtitle")
                    current_pos = end_pos + 12
                else:
                    current_pos = next_marker_pos + 11
                    
            elif next_marker_tag == 'important':
                end_pos = text.find('§/IMPORTANT§', next_marker_pos)
                if end_pos != -1:
                    important_text = text[next_marker_pos + 11:end_pos]
                    self.suggestions_text.insert(tk.END, important_text, "important")
                    current_pos = end_pos + 12
                else:
                    current_pos = next_marker_pos + 11
                    
            elif next_marker_tag == 'emphasis':
                end_pos = text.find('§/EMPHASIS§', next_marker_pos)
                if end_pos != -1:
                    emphasis_text = text[next_marker_pos + 10:end_pos]
                    self.suggestions_text.insert(tk.END, emphasis_text, "emphasis")
                    current_pos = end_pos + 11
                else:
                    current_pos = next_marker_pos + 10
                    
            elif next_marker_tag == 'code':
                end_pos = text.find('§/CODE§', next_marker_pos)
                if end_pos != -1:
                    code_text = text[next_marker_pos + 6:end_pos]
                    self.suggestions_text.insert(tk.END, code_text, "code")
                    current_pos = end_pos + 7
                else:
                    current_pos = next_marker_pos + 6
    
    def display_suggestions(self, suggestions):
        # Очистка контейнера подсказок
        for widget in self.suggestions_scrollable_frame.winfo_children():
            widget.destroy()
        
        if not suggestions:
            # Создаем блок с сообщением об отсутствии подсказок
            no_suggestions_frame = ctk.CTkFrame(self.suggestions_scrollable_frame, 
                                               corner_radius=8)
            no_suggestions_frame.pack(fill=tk.X, pady=(0, 8), padx=3)
            
            no_suggestions_label = ctk.CTkLabel(no_suggestions_frame, text="Подсказки не найдены", 
                                               font=ctk.CTkFont(size=12))
            no_suggestions_label.pack(pady=12)
        else:
            for i, suggestion in enumerate(suggestions, 1):
                self.create_suggestion_block(i, suggestion)
    
    def create_suggestion_block(self, index, suggestion):
        """Создание блока для одной подсказки с скругленными углами"""
        title = suggestion.get("title", f"Подсказка {index}")
        content = suggestion.get("content", "")
        
        # Основной фрейм блока
        block_frame = ctk.CTkFrame(self.suggestions_scrollable_frame, 
                                  corner_radius=8,
                                  fg_color=("#2b2b2b", "#1a1a1a"))
        block_frame.pack(fill=tk.X, pady=(0, 8), padx=3)
        
        # Заголовок блока
        header_frame = ctk.CTkFrame(block_frame, fg_color="transparent")
        header_frame.pack(fill=tk.X, padx=12, pady=(8, 0))
        
        number_label = ctk.CTkLabel(header_frame, text=f"{index}", 
                                   font=ctk.CTkFont(size=14, weight="bold"),
                                   text_color="#4CAF50")
        number_label.pack(side=tk.LEFT)
        
        title_label = ctk.CTkLabel(header_frame, text=title, 
                                  font=ctk.CTkFont(size=14, weight="bold"))
        title_label.pack(side=tk.LEFT, padx=(8, 0))
        
        # Контент блока
        if content:
            # Преобразуем HTML в читаемый плоский текст с переносами и маркерами
            display_text = self.html_to_display_text(content)

            # Отображаем простой, всегда видимый текст (без редактирования)
            content_label = ctk.CTkLabel(
                block_frame,
                text=display_text,
                font=ctk.CTkFont(size=12),
                justify=tk.LEFT,
                anchor="w",
                wraplength=280,
            )
            content_label.pack(fill=tk.X, padx=12, pady=(8, 12))

    def html_to_display_text(self, html_content: str) -> str:
        """Грубое преобразование HTML-подобного содержимого в читаемый текст.
        Сохраняем переносы строк и маркеры списков, убираем декоративные теги."""
        text = html_content or ""
        # Переносы
        text = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
        # Списки
        text = text.replace("<ul>", "\n").replace("</ul>", "\n")
        text = text.replace("<li>", "• ").replace("</li>", "\n")
        # Заголовки и выделения — просто убираем теги
        replacements = [
            ("<h3>", ""), ("</h3>", ""),
            ("<strong>", ""), ("</strong>", ""),
            ("<em>", ""), ("</em>", ""),
            ("<code>", ""), ("</code>", ""),
            ("<p>", ""), ("</p>", "\n"),
        ]
        for src, dst in replacements:
            text = text.replace(src, dst)
        # Убираем любые оставшиеся угловые теги простой заменой
        # (избегаем regex, чтобы не тянуть зависимости)
        while "<" in text and ">" in text:
            start = text.find("<")
            end = text.find(">", start)
            if end == -1:
                break
            text = text[:start] + text[end+1:]
        # Нормализуем пустые строки
        lines = [ln.rstrip() for ln in text.splitlines()]
        # Удаляем ведущие/замыкающие пустые строки
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines)
    
    def insert_formatted_text_to_widget(self, text_widget, text):
        """Вставка текста с форматированием в указанный виджет"""
        current_pos = 0
        
        while current_pos < len(text):
            # Ищем маркеры форматирования
            subtitle_start = text.find('§SUBTITLE§', current_pos)
            important_start = text.find('§IMPORTANT§', current_pos)
            emphasis_start = text.find('§EMPHASIS§', current_pos)
            code_start = text.find('§CODE§', current_pos)
            
            # Находим ближайший маркер
            markers = [(subtitle_start, 'subtitle'), (important_start, 'important'), 
                      (emphasis_start, 'emphasis'), (code_start, 'code')]
            markers = [(pos, tag) for pos, tag in markers if pos != -1]
            
            if not markers:
                # Вставляем оставшийся текст без форматирования
                remaining_text = text[current_pos:]
                if remaining_text:
                    text_widget.insert(tk.END, remaining_text)
                break
            
            # Сортируем по позиции
            markers.sort(key=lambda x: x[0])
            next_marker_pos, next_marker_tag = markers[0]
            
            # Вставляем текст до маркера
            if next_marker_pos > current_pos:
                plain_text = text[current_pos:next_marker_pos]
                text_widget.insert(tk.END, plain_text)
            
            # Обрабатываем маркер
            if next_marker_tag == 'subtitle':
                end_pos = text.find('§/SUBTITLE§', next_marker_pos)
                if end_pos != -1:
                    subtitle_text = text[next_marker_pos + 11:end_pos]
                    text_widget.insert(tk.END, subtitle_text, "subtitle")
                    current_pos = end_pos + 12
                else:
                    current_pos = next_marker_pos + 11
                    
            elif next_marker_tag == 'important':
                end_pos = text.find('§/IMPORTANT§', next_marker_pos)
                if end_pos != -1:
                    important_text = text[next_marker_pos + 11:end_pos]
                    text_widget.insert(tk.END, important_text, "important")
                    current_pos = end_pos + 12
                else:
                    current_pos = next_marker_pos + 11
                    
            elif next_marker_tag == 'emphasis':
                end_pos = text.find('§/EMPHASIS§', next_marker_pos)
                if end_pos != -1:
                    emphasis_text = text[next_marker_pos + 10:end_pos]
                    text_widget.insert(tk.END, emphasis_text, "emphasis")
                    current_pos = end_pos + 11
                else:
                    current_pos = next_marker_pos + 10
                    
            elif next_marker_tag == 'code':
                end_pos = text.find('§/CODE§', next_marker_pos)
                if end_pos != -1:
                    code_text = text[next_marker_pos + 6:end_pos]
                    text_widget.insert(tk.END, code_text, "code")
                    current_pos = end_pos + 7
                else:
                    current_pos = next_marker_pos + 6
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = RelevatorPanel()
    app.run() 
