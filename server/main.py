import os
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()

app = FastAPI(title="Relevator Server")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация OpenAI клиента с ProxyAPI
api_key = os.getenv("PROXY_API_KEY")
base_url = os.getenv("PROXY_BASE_URL")

client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)

class ScreenshotRequest(BaseModel):
    image_data: str  # base64 encoded image

class ScreenshotsRequest(BaseModel):
    screenshots: List[str]  # список base64 encoded images

class SuggestionResponse(BaseModel):
    suggestions: List[dict]

@app.post("/process-screenshot", response_model=SuggestionResponse)
async def process_screenshot(request: ScreenshotRequest):
    try:
        # Системный промпт
        system_prompt = """Ты - помощник, который анализирует скриншоты и предоставляет полезные подсказки. 
        Анализируй контекст изображения и давай от 1 до 3 практических советов или подсказок.
        Каждая подсказка должна иметь название и содержание.
        
        Форматируй содержание в HTML:
        - Используй <h3> для подзаголовков
        - Используй <ul><li> для списков
        - Используй <strong> для важных моментов
        - Используй <em> для акцентов
        - Используй <code> для команд или кода
        - Используй <br> для переносов строк"""
        
        # Функция для структурированного вывода
        functions_analyze_image = [
            {
                "name": "process_screenshot",
                "description": "Проанализируй изображение скриншота и предоставь подсказки.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "suggestions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string", "description": "Название подсказки"},
                                    "content": {"type": "string", "description": "Содержание подсказки"}
                                },
                                "required": ["title", "content"]
                            },
                            "description": "Массив из 1-3 подсказок"
                        }
                    },
                    "required": ["suggestions"]
                }
            }
        ]
        
        # Подготавливаем сообщения для GPT с изображением
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{request.image_data}",
                            "detail": "low"
                        }
                    },
                    {
                        "type": "text",
                        "text": "Проанализируй этот скриншот и дай 1-3 полезные подсказки с названиями и содержанием."
                    }
                ]
            }
        ]
        
        # Запрос к GPT-4o с изображением
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            functions=functions_analyze_image,
            function_call={"name": "process_screenshot"}
        )
        
        # Парсинг структурированного ответа
        if response.choices and response.choices[0].message:
            assistant_message = response.choices[0].message
            function_call = assistant_message.function_call if hasattr(assistant_message, 'function_call') else {}
            arguments = function_call.arguments if hasattr(function_call, 'arguments') else '{}'
            result = json.loads(arguments)
            suggestions = result.get("suggestions", [])
            
            return SuggestionResponse(suggestions=suggestions)
        else:
            raise HTTPException(status_code=400, detail="Некорректный или пустой ответ")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки: {str(e)}")

@app.post("/process-screenshots", response_model=SuggestionResponse)
async def process_screenshots(request: ScreenshotsRequest):
    try:
        # Системный промпт для множественных скриншотов
        system_prompt = """Ты - помощник, который анализирует серию скриншотов и предоставляет полезные подсказки. 
        Анализируй контекст всех изображений как единую последовательность действий пользователя.
        Давай от 1 до 3 практических советов или подсказок на основе всей серии.
        Каждая подсказка должна иметь название и содержание.
        
        Форматируй содержание в HTML:
        - Используй <h3> для подзаголовков
        - Используй <ul><li> для списков
        - Используй <strong> для важных моментов
        - Используй <em> для акцентов
        - Используй <code> для команд или кода
        - Используй <br> для переносов строк"""
        
        # Функция для структурированного вывода
        functions_analyze_image = [
            {
                "name": "process_screenshots",
                "description": "Проанализируй серию изображений скриншотов и предоставь подсказки.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "suggestions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string", "description": "Название подсказки"},
                                    "content": {"type": "string", "description": "Содержание подсказки"}
                                },
                                "required": ["title", "content"]
                            },
                            "description": "Массив из 1-3 подсказок"
                        }
                    },
                    "required": ["suggestions"]
                }
            }
        ]
        
        # Подготавливаем сообщения для GPT с изображениями
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Добавляем изображения в сообщение пользователя
        user_content = []
        for i, image_data_b64 in enumerate(request.screenshots):
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_data_b64}",
                    "detail": "low"
                }
            })
        
        # Добавляем текстовое описание
        user_content.append({
            "type": "text",
            "text": f"Проанализируй эти {len(request.screenshots)} скриншотов как последовательность действий пользователя и дай 1-3 полезные подсказки с названиями и содержанием."
        })
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        # Запрос к GPT-4o с изображениями
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            functions=functions_analyze_image,
            function_call={"name": "process_screenshots"}
        )
        
        # Парсинг структурированного ответа
        if response.choices and response.choices[0].message:
            assistant_message = response.choices[0].message
            function_call = assistant_message.function_call if hasattr(assistant_message, 'function_call') else {}
            arguments = function_call.arguments if hasattr(function_call, 'arguments') else '{}'
            result = json.loads(arguments)
            suggestions = result.get("suggestions", [])
            
            return SuggestionResponse(suggestions=suggestions)
        else:
            raise HTTPException(status_code=400, detail="Некорректный или пустой ответ")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 