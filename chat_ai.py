"""Модуль для работы с OpenAI API для анализа чата"""
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI


class ChatAnalyzerAI:
    """AI анализатор чата через OpenAI"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"
    
    def ask_question(
        self, 
        question: str, 
        analysis: Dict, 
        messages_sample: List[Dict] = None,
        conversation_history: List[Dict] = None,
        day_analysis: Dict = None
    ) -> str:
        """
        Задать вопрос AI о чате
        
        Args:
            question: Вопрос пользователя
            analysis: Полный анализ чата (статистика)
            messages_sample: Примеры сообщений (первые и последние N)
            conversation_history: История разговора с AI
        """
        
        # Формируем системный промпт
        system_prompt = """Ты умный помощник для анализа переписки WhatsApp. 
Ты помогаешь пользователю понять интересные паттерны, статистику и особенности его чата.

У тебя есть доступ к:
1. Полной статистике чата (количество сообщений, слова, эмодзи, активность и т.д.)
2. Примерам сообщений из переписки
3. Анализу активности по времени, участникам и т.д.

Отвечай:
- Кратко и по делу
- Используй конкретные цифры из статистики
- Находи интересные паттерны и закономерности
- Будь дружелюбным и понятным
- Если нужно больше данных для ответа, скажи об этом

Отвечай на русском языке."""
        
        # Формируем контекст с анализом
        analysis_summary = self._format_analysis(analysis)
        
        # Добавляем анализ конкретного дня, если указан
        day_context = ""
        if day_analysis and 'error' not in day_analysis:
            day_context = "\n\n📅 АНАЛИЗ КОНКРЕТНОГО ДНЯ:\n"
            day_context += f"Дата: {day_analysis.get('date', 'Неизвестно')}\n"
            
            if 'basic' in day_analysis:
                basic = day_analysis['basic']
                day_context += f"- Сообщений за день: {basic.get('total_messages', 0)}\n"
                day_context += f"- Слов: {basic.get('total_words', 0)}\n"
                day_context += f"- Средняя длина сообщения: {basic.get('avg_message_length', 0):.0f} символов\n"
            
            # Получаем статистику по участникам из basic
            if 'basic' in day_analysis and 'author_stats' in day_analysis['basic']:
                day_context += "\nПо участникам:\n"
                for author, count in day_analysis['basic']['author_stats'].items():
                    day_context += f"- {author}: {count} сообщений\n"
            
            if 'activity' in day_analysis and 'hourly' in day_analysis['activity']:
                hourly = day_analysis['activity']['hourly']
                if hourly:
                    max_hour = max(hourly, key=lambda x: x[1])
                    day_context += f"\nСамый активный час: {max_hour[0]}:00 ({max_hour[1]} сообщений)\n"
            
            # Получаем топ слов из структуры words
            if 'words' in day_analysis and 'top_words' in day_analysis['words']:
                words = day_analysis['words']['top_words'][:5]
                if words:
                    day_context += f"\nТоп-5 слов: {', '.join([f'{w[0]} ({w[1]})' for w in words])}\n"
            
            day_context += "\nВАЖНО: Пользователь задает вопрос о КОНКРЕТНОМ ДНЕ. Отвечай с учетом анализа этого дня!"
        
        # Добавляем примеры сообщений
        messages_context = ""
        if messages_sample:
            # Берем первые 30 и последние 30 сообщений для контекста
            sample_size = min(30, len(messages_sample))
            first_messages = messages_sample[:sample_size]
            last_messages = messages_sample[-sample_size:] if len(messages_sample) > sample_size else []
            
            messages_context = "\n\nПримеры сообщений из переписки (для понимания стиля общения):\n"
            messages_context += "Первые сообщения:\n"
            for msg in first_messages[:15]:  # Первые 15
                text = msg.get('text', '')[:150]  # Ограничиваем длину
                messages_context += f"- [{msg.get('date', '')} {msg.get('time', '')}] {msg.get('author', '')}: {text}\n"
            
            if last_messages:
                messages_context += "\nПоследние сообщения:\n"
                for msg in last_messages[-15:]:  # Последние 15
                    text = msg.get('text', '')[:150]
                    messages_context += f"- [{msg.get('date', '')} {msg.get('time', '')}] {msg.get('author', '')}: {text}\n"
        
        # Формируем сообщения для API
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Добавляем историю разговора
        if conversation_history and len(conversation_history) > 0:
            # Если есть история, просто добавляем её
            for msg in conversation_history:
                messages.append(msg)
        else:
            # Первое сообщение с контекстом
            context_parts = [f"Вот статистика и анализ чата:\n\n{analysis_summary}"]
            
            if day_context:
                context_parts.append(day_context)
            
            if messages_context:
                context_parts.append(messages_context)
            
            context_parts.append("\nТеперь отвечай на вопросы пользователя о его переписке.")
            
            context_message = "\n".join(context_parts)
            messages.append({"role": "user", "content": context_message})
        
        # Добавляем текущий вопрос
        messages.append({"role": "user", "content": question})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise ValueError(f"Ошибка OpenAI API: {str(e)}")
    
    def _format_analysis(self, analysis: Dict) -> str:
        """Форматирует анализ для передачи в AI"""
        if not analysis or 'error' in analysis:
            return "Анализ недоступен"
        
        summary = "СТАТИСТИКА ЧАТА:\n\n"
        
        # Базовая статистика
        if 'basic' in analysis:
            basic = analysis['basic']
            summary += f"📊 Общая статистика:\n"
            summary += f"- Всего сообщений: {basic.get('total_messages', 0):,}\n"
            summary += f"- Всего слов: {basic.get('total_words', 0):,}\n"
            summary += f"- Дней активности: {basic.get('days_active', 0)}\n"
            summary += f"- Сообщений в день: {basic.get('messages_per_day', 0):.1f}\n"
            summary += f"- Средняя длина сообщения: {basic.get('avg_message_length', 0):.0f} символов\n\n"
            
            # Статистика по участникам
            if 'author_stats' in basic:
                summary += "👥 По участникам:\n"
                for author, count in basic['author_stats'].items():
                    percentage = (count / basic['total_messages'] * 100) if basic['total_messages'] > 0 else 0
                    summary += f"- {author}: {count:,} сообщений ({percentage:.1f}%)\n"
                summary += "\n"
        
        # Эмодзи
        if 'emoji' in analysis:
            emoji = analysis['emoji']
            summary += f"😊 Эмодзи:\n"
            summary += f"- Всего использований: {emoji.get('total_emojis', 0):,}\n"
            summary += f"- Уникальных эмодзи: {emoji.get('unique_emojis', 0)}\n"
            summary += f"- Сообщений с эмодзи: {emoji.get('messages_with_emoji', 0):,} ({emoji.get('emoji_usage_percentage', 0):.1f}%)\n"
            if 'top_emojis' in emoji and emoji['top_emojis']:
                summary += f"- Топ-5 эмодзи: {', '.join([f'{e[0]} ({e[1]})' for e in emoji['top_emojis'][:5]])}\n"
            summary += "\n"
        
        # Топ слов
        if 'words' in analysis and 'top_words' in analysis['words']:
            words = analysis['words']['top_words'][:10]
            if words:
                summary += f"📝 Топ-10 слов: {', '.join([f'{w[0]} ({w[1]})' for w in words])}\n\n"
        
        # Активность
        if 'activity' in analysis:
            activity = analysis['activity']
            if 'hourly' in activity:
                # Находим самый активный час
                hourly = activity['hourly']
                max_hour = max(hourly, key=lambda x: x[1])
                summary += f"⏰ Самый активный час: {max_hour[0]}:00 ({max_hour[1]} сообщений)\n"
            
            if 'weekday' in activity:
                weekday = activity['weekday']
                max_day = max(weekday, key=lambda x: x[1])
                summary += f"📅 Самый активный день недели: {max_day[0]} ({max_day[1]} сообщений)\n"
            summary += "\n"
        
        # Интересные факты
        if 'interesting' in analysis:
            interesting = analysis['interesting']
            if 'top_active_days' in interesting and interesting['top_active_days']:
                top_day = interesting['top_active_days'][0]
                summary += f"🔥 Самый активный день: {top_day['date']} ({top_day['messages']} сообщений)\n"
            if 'avg_response_time_minutes' in interesting:
                summary += f"⚡ Среднее время ответа: {interesting['avg_response_time_minutes']:.1f} минут\n"
            summary += "\n"
        
        return summary

