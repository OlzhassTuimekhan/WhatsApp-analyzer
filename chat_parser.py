import re
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple
import emoji


class ChatParser:
    """Парсер WhatsApp чата"""
    
    # Регулярное выражение для парсинга сообщений
    MESSAGE_PATTERN = re.compile(
        r'\[(\d{2}\.\d{2}\.\d{4}),\s*(\d{2}:\d{2}:\d{2})\]\s*([^:]+):\s*(.*)'
    )
    
    # Для системных сообщений (image omitted, document omitted и т.д.)
    SYSTEM_PATTERN = re.compile(
        r'[‎\s]*\[(\d{2}\.\d{2}\.\d{4}),\s*(\d{2}:\d{2}:\d{2})\]\s*([^:]+):\s*[‎\s]*(.*)'
    )
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.messages = []
        
    def parse(self) -> List[Dict]:
        """Парсит файл чата и возвращает список сообщений"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_message = None
        current_text = []
        
        for line in lines:
            # Убираем невидимые символы в начале (например, ‎)
            line = line.lstrip('\u200E\u200F\u202A-\u202E\u2066-\u2069').strip()
            if not line:
                continue
            
            # Пытаемся распарсить новое сообщение
            match = self.MESSAGE_PATTERN.match(line)
            if match:
                # Сохраняем предыдущее сообщение, если есть
                if current_message:
                    current_message['text'] = ' '.join(current_text).strip()
                    self.messages.append(current_message)
                
                # Начинаем новое сообщение
                date_str, time_str, author, text = match.groups()
                
                try:
                    # Парсим дату и время
                    datetime_str = f"{date_str} {time_str}"
                    dt = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M:%S")
                    
                    current_message = {
                        'datetime': dt,
                        'date': dt.date(),
                        'time': dt.time(),
                        'hour': dt.hour,
                        'weekday': dt.weekday(),  # 0 = Monday, 6 = Sunday
                        'author': author.strip(),
                        'text': text.strip(),
                    }
                    current_text = [text.strip()] if text.strip() else []
                except ValueError:
                    # Если не получилось распарсить, добавляем к текущему сообщению
                    if current_message:
                        current_text.append(line)
                    continue
            else:
                # Продолжение предыдущего сообщения (многострочное)
                if current_message:
                    current_text.append(line)
                else:
                    # Системное сообщение или нераспознанная строка
                    system_match = self.SYSTEM_PATTERN.match(line)
                    if system_match:
                        date_str, time_str, author, text = system_match.groups()
                        try:
                            datetime_str = f"{date_str} {time_str}"
                            dt = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M:%S")
                            
                            current_message = {
                                'datetime': dt,
                                'date': dt.date(),
                                'time': dt.time(),
                                'hour': dt.hour,
                                'weekday': dt.weekday(),
                                'author': author.strip(),
                                'text': text.strip() if text.strip() else line,
                            }
                            current_text = []
                        except ValueError:
                            pass
        
        # Сохраняем последнее сообщение
        if current_message:
            current_message['text'] = ' '.join(current_text).strip()
            self.messages.append(current_message)
        
        return self.messages


class ChatAnalyzer:
    """Анализатор чата с различной статистикой"""
    
    def __init__(self, messages: List[Dict]):
        self.messages = messages
    
    def get_basic_stats(self) -> Dict:
        """Базовая статистика"""
        total_messages = len(self.messages)
        
        if total_messages == 0:
            return {}
        
        # Период чата
        dates = [msg['date'] for msg in self.messages]
        first_date = min(dates)
        last_date = max(dates)
        days_active = (last_date - first_date).days + 1
        
        # Статистика по авторам
        author_stats = defaultdict(int)
        author_chars = defaultdict(int)
        
        for msg in self.messages:
            author = msg['author']
            author_stats[author] += 1
            author_chars[author] += len(msg['text'])
        
        # Общее количество символов и слов
        total_chars = sum(len(msg['text']) for msg in self.messages)
        total_words = sum(len(msg['text'].split()) for msg in self.messages)
        
        # Средние значения
        avg_message_length = total_chars / total_messages if total_messages > 0 else 0
        avg_words_per_message = total_words / total_messages if total_messages > 0 else 0
        
        return {
            'total_messages': total_messages,
            'total_chars': total_chars,
            'total_words': total_words,
            'first_date': first_date.isoformat(),
            'last_date': last_date.isoformat(),
            'days_active': days_active,
            'avg_message_length': round(avg_message_length, 2),
            'avg_words_per_message': round(avg_words_per_message, 2),
            'messages_per_day': round(total_messages / days_active, 2) if days_active > 0 else 0,
            'author_stats': dict(author_stats),
            'author_chars': dict(author_chars),
        }
    
    def get_emoji_stats(self) -> Dict:
        """Статистика по эмодзи/смайликам"""
        emoji_counter = defaultdict(int)
        emoji_messages = []
        
        for msg in self.messages:
            text = msg['text']
            # Извлекаем все эмодзи
            emojis_in_msg = [char for char in text if char in emoji.EMOJI_DATA]
            
            if emojis_in_msg:
                emoji_messages.append(msg)
                for emoji_char in emojis_in_msg:
                    emoji_counter[emoji_char] += 1
        
        # Топ эмодзи
        top_emojis = sorted(emoji_counter.items(), key=lambda x: x[1], reverse=True)[:50]
        
        # Статистика по авторам
        author_emoji_stats = defaultdict(lambda: {'count': 0, 'unique': set()})
        
        for msg in emoji_messages:
            author = msg['author']
            emojis_in_msg = [char for char in msg['text'] if char in emoji.EMOJI_DATA]
            author_emoji_stats[author]['count'] += len(emojis_in_msg)
            author_emoji_stats[author]['unique'].update(emojis_in_msg)
        
        # Преобразуем sets в counts
        for author in author_emoji_stats:
            author_emoji_stats[author]['unique'] = len(author_emoji_stats[author]['unique'])
        
        return {
            'total_emojis': sum(emoji_counter.values()),
            'unique_emojis': len(emoji_counter),
            'messages_with_emoji': len(emoji_messages),
            'emoji_usage_percentage': round(len(emoji_messages) / len(self.messages) * 100, 2) if self.messages else 0,
            'top_emojis': [(char, count) for char, count in top_emojis],
            'author_emoji_stats': {k: dict(v) for k, v in author_emoji_stats.items()},
        }
    
    def get_word_stats(self, min_word_length: int = 2, top_n: int = 50) -> Dict:
        """Статистика по словам"""
        word_counter = defaultdict(int)
        
        # Список стоп-слов (можно расширить)
        stop_words = {
            'и', 'в', 'на', 'с', 'к', 'а', 'о', 'у', 'я', 'ты', 'мы', 'вы', 'он', 'она', 'они',
            'это', 'как', 'так', 'что', 'для', 'от', 'до', 'за', 'из', 'же', 'бы', 'ли', 'то',
            'но', 'да', 'нет', 'не', 'да', 'ж', 'же', 'ну', 'вот', 'там', 'тут',
            # Английские стоп-слова
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            # Казахские
            'мен', 'сен', 'ол', 'біз', 'сіз', 'олар', 'бен', 'менен', 'менің', 'сенің', 'оның',
        }
        
        for msg in self.messages:
            text = msg['text'].lower()
            # Убираем пунктуацию и разбиваем на слова
            words = re.findall(r'\b\w+\b', text)
            
            for word in words:
                if len(word) >= min_word_length and word not in stop_words:
                    word_counter[word] += 1
        
        top_words = sorted(word_counter.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        return {
            'total_unique_words': len(word_counter),
            'top_words': top_words,
        }
    
    def get_activity_stats(self) -> Dict:
        """Статистика активности по времени"""
        # По часам
        hourly_activity = defaultdict(int)
        
        # По дням недели
        weekday_activity = defaultdict(int)
        weekday_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        
        # По месяцам
        monthly_activity = defaultdict(int)
        
        # По авторам по часам
        author_hourly = defaultdict(lambda: defaultdict(int))
        
        for msg in self.messages:
            hour = msg['hour']
            weekday = msg['weekday']
            month = msg['datetime'].strftime('%Y-%m')
            
            hourly_activity[hour] += 1
            weekday_activity[weekday] += 1
            monthly_activity[month] += 1
            
            author_hourly[msg['author']][hour] += 1
        
        # Преобразуем в списки для удобства
        hourly_list = [(h, hourly_activity[h]) for h in range(24)]
        weekday_list = [(weekday_names[w], weekday_activity[w]) for w in range(7)]
        monthly_list = sorted(monthly_activity.items())
        
        return {
            'hourly': hourly_list,
            'weekday': weekday_list,
            'monthly': monthly_list,
            'author_hourly': {author: [(h, count) for h, count in sorted(hours.items())] 
                             for author, hours in author_hourly.items()},
        }
    
    def get_message_length_stats(self) -> Dict:
        """Статистика по длине сообщений"""
        lengths = [len(msg['text']) for msg in self.messages]
        
        if not lengths:
            return {}
        
        author_lengths = defaultdict(list)
        for msg in self.messages:
            author_lengths[msg['author']].append(len(msg['text']))
        
        # Средние длины по авторам
        author_avg_lengths = {
            author: round(sum(lengths) / len(lengths), 2) 
            for author, lengths in author_lengths.items()
        }
        
        return {
            'min_length': min(lengths),
            'max_length': max(lengths),
            'avg_length': round(sum(lengths) / len(lengths), 2),
            'median_length': sorted(lengths)[len(lengths) // 2],
            'author_avg_lengths': author_avg_lengths,
        }
    
    def search_word(self, word: str, case_sensitive: bool = False) -> Dict:
        """Поиск слова с детальной статистикой"""
        word_lower = word.lower()
        
        matches = []
        author_stats = defaultdict(int)
        hour_stats = defaultdict(int)
        weekday_stats = defaultdict(int)
        date_stats = defaultdict(int)
        
        for msg in self.messages:
            text = msg['text']
            
            if not case_sensitive:
                text_lower = text.lower()
                search_text = text_lower
                search_word = word_lower
            else:
                search_text = text
                search_word = word
            
            if search_word in search_text:
                # Находим все вхождения
                count = search_text.count(search_word)
                
                matches.append({
                    'datetime': msg['datetime'].isoformat(),
                    'date': msg['date'].isoformat(),
                    'time': msg['time'].isoformat(),
                    'hour': msg['hour'],
                    'weekday': msg['weekday'],
                    'author': msg['author'],
                    'text': msg['text'],
                    'count': count,
                })
                
                author_stats[msg['author']] += count
                hour_stats[msg['hour']] += count
                weekday_stats[msg['weekday']] += count
                date_stats[msg['date']] += count
        
        # Сортируем по дате
        matches.sort(key=lambda x: x['datetime'])
        
        # Статистика
        total_matches = sum(msg['count'] for msg in matches)
        unique_messages = len(matches)
        
        # Процент использования по авторам
        total_author_msgs = defaultdict(int)
        for msg in self.messages:
            total_author_msgs[msg['author']] += 1
        
        author_percentages = {
            author: round((stats / total_author_msgs[author] * 100), 2) 
            if total_author_msgs[author] > 0 else 0
            for author, stats in author_stats.items()
        }
        
        weekday_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        
        return {
            'word': word,
            'total_occurrences': total_matches,
            'unique_messages': unique_messages,
            'author_stats': dict(author_stats),
            'author_percentages': author_percentages,
            'hour_stats': [(h, hour_stats[h]) for h in sorted(hour_stats.keys())],
            'weekday_stats': [(weekday_names[w], weekday_stats[w]) for w in sorted(weekday_stats.keys())],
            'date_stats': sorted(date_stats.items()),
            'matches': matches,  # Возвращаем все сообщения
            'total_matches_count': len(matches),
        }
    
    def get_message_context(self, message_datetime: str, context_size: int = 10) -> Dict:
        """Получить контекст вокруг сообщения: предыдущие и следующие N сообщений"""
        try:
            # Парсим дату из ISO формата
            if 'T' in message_datetime:
                target_dt = datetime.fromisoformat(message_datetime.replace('Z', '+00:00'))
            else:
                target_dt = datetime.fromisoformat(message_datetime)
        except Exception as e:
            # Пробуем парсить как строку без секунд
            try:
                target_dt = datetime.fromisoformat(message_datetime.replace('Z', ''))
            except:
                return {'error': f'Не удалось распарсить дату: {str(e)}'}
        
        # Находим индекс сообщения (сравниваем с точностью до секунды)
        target_idx = None
        target_dt_normalized = target_dt.replace(microsecond=0)
        
        for i, msg in enumerate(self.messages):
            msg_dt_normalized = msg['datetime'].replace(microsecond=0)
            if msg_dt_normalized == target_dt_normalized:
                target_idx = i
                break
        
        if target_idx is None:
            # Пробуем найти ближайшее сообщение по времени (в пределах 1 минуты)
            min_diff = None
            closest_idx = None
            for i, msg in enumerate(self.messages):
                diff = abs((msg['datetime'] - target_dt).total_seconds())
                if diff < 60:  # В пределах минуты
                    if min_diff is None or diff < min_diff:
                        min_diff = diff
                        closest_idx = i
            
            if closest_idx is not None:
                target_idx = closest_idx
            else:
                return {'error': 'Сообщение не найдено'}
        
        # Берем контекст
        start_idx = max(0, target_idx - context_size)
        end_idx = min(len(self.messages), target_idx + context_size + 1)
        
        context_messages = []
        for i in range(start_idx, end_idx):
            msg = self.messages[i].copy()
            msg['datetime'] = msg['datetime'].isoformat()
            msg['date'] = msg['date'].isoformat()
            msg['time'] = msg['time'].isoformat()
            context_messages.append(msg)
        
        return {
            'target_index': target_idx - start_idx,  # Индекс целевого сообщения в контексте
            'messages': context_messages,
            'total': len(context_messages),
        }
    
    def get_interesting_stats(self) -> Dict:
        """Интересная статистика: самые длинные/короткие сообщения, топ дни и т.д."""
        if not self.messages:
            return {}
        
        # Самые длинные сообщения
        sorted_by_length = sorted(self.messages, key=lambda x: len(x['text']), reverse=True)
        longest_messages = [
            {
                'text': msg['text'][:200] + ('...' if len(msg['text']) > 200 else ''),
                'length': len(msg['text']),
                'author': msg['author'],
                'date': msg['date'].isoformat(),
            }
            for msg in sorted_by_length[:10]
        ]
        
        # Самые короткие (непустые) сообщения
        non_empty = [msg for msg in self.messages if msg['text'].strip()]
        shortest_messages = sorted(non_empty, key=lambda x: len(x['text']))[:10]
        shortest_list = [
            {
                'text': msg['text'],
                'length': len(msg['text']),
                'author': msg['author'],
                'date': msg['date'].isoformat(),
            }
            for msg in shortest_messages
        ]
        
        # Дни с наибольшей активностью
        date_activity = defaultdict(int)
        for msg in self.messages:
            date_activity[msg['date']] += 1
        
        top_active_days = sorted(date_activity.items(), key=lambda x: x[1], reverse=True)[:10]
        top_days = [
            {
                'date': date.isoformat(),
                'messages': count
            }
            for date, count in top_active_days
        ]
        
        # Время первого и последнего сообщения каждого участника
        author_first = {}  # Храним datetime объекты для сравнения
        author_last = {}
        
        for msg in self.messages:
            author = msg['author']
            dt = msg['datetime']
            
            if author not in author_first or dt < author_first[author]['datetime']:
                author_first[author] = {
                    'datetime': dt,  # Храним datetime для сравнения
                    'text': msg['text'][:100]
                }
            
            if author not in author_last or dt > author_last[author]['datetime']:
                author_last[author] = {
                    'datetime': dt,  # Храним datetime для сравнения
                    'text': msg['text'][:100]
                }
        
        # Сериализуем datetime перед возвратом
        author_first_serialized = {
            k: {
                'datetime': v['datetime'].isoformat(),
                'date': v['datetime'].date().isoformat(),
                'time': v['datetime'].time().isoformat(),
                'text': v['text']
            }
            for k, v in author_first.items()
        }
        
        author_last_serialized = {
            k: {
                'datetime': v['datetime'].isoformat(),
                'date': v['datetime'].date().isoformat(),
                'time': v['datetime'].time().isoformat(),
                'text': v['text']
            }
            for k, v in author_last.items()
        }
        
        # Среднее время ответа (время между сообщениями разных авторов)
        response_times = []
        prev_msg = None
        for msg in sorted(self.messages, key=lambda x: x['datetime']):
            if prev_msg and prev_msg['author'] != msg['author']:
                delta = (msg['datetime'] - prev_msg['datetime']).total_seconds() / 60  # в минутах
                if 0 < delta < 24 * 60:  # Только разумные значения (до суток)
                    response_times.append(delta)
            prev_msg = msg
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'longest_messages': longest_messages,
            'shortest_messages': shortest_list,
            'top_active_days': top_days,
            'author_first_message': author_first_serialized,
            'author_last_message': author_last_serialized,
            'avg_response_time_minutes': round(avg_response_time, 2),
            'total_responses_analyzed': len(response_times),
        }
    
    def get_messages_by_hour(self, hour: int, date: str = None) -> Dict:
        """Получить сообщения за конкретный час (опционально за конкретную дату)"""
        from datetime import date as date_type
        
        filtered_messages = []
        
        for msg in self.messages:
            if msg['hour'] == hour:
                if date:
                    # Если указана дата, фильтруем по дате
                    try:
                        target_date_obj = date_type.fromisoformat(date) if isinstance(date, str) else date
                        if msg['date'] == target_date_obj:
                            filtered_messages.append(msg)
                    except:
                        continue
                else:
                    # Без даты - все сообщения за этот час
                    filtered_messages.append(msg)
        
        if not filtered_messages:
            return {'error': f'Нет сообщений за {hour}:00' + (f' {date}' if date else '')}
        
        # Сортируем по дате
        filtered_messages.sort(key=lambda x: x['datetime'])
        
        return {
            'hour': hour,
            'date': date,
            'total_messages': len(filtered_messages),
            'messages': [
                {
                    'datetime': msg['datetime'].isoformat(),
                    'date': msg['date'].isoformat(),
                    'time': msg['time'].isoformat(),
                    'author': msg['author'],
                    'text': msg['text'],
                }
                for msg in filtered_messages
            ],
        }
    
    def get_day_analysis(self, target_date: str) -> Dict:
        """Полный анализ конкретного дня"""
        from datetime import date as date_type
        
        try:
            # Парсим дату
            if isinstance(target_date, str):
                target_date_obj = date_type.fromisoformat(target_date)
            else:
                target_date_obj = target_date
            
            # Фильтруем сообщения за этот день
            day_messages = [msg for msg in self.messages if msg['date'] == target_date_obj]
            
            if not day_messages:
                return {'error': f'Нет сообщений за {target_date_obj.isoformat()}'}
            
            # Создаем временный анализатор только для сообщений этого дня
            day_analyzer = ChatAnalyzer(day_messages)
            
            # Получаем всю статистику для дня
            analysis = {
                'date': target_date_obj.isoformat(),
                'basic': day_analyzer.get_basic_stats(),
                'emoji': day_analyzer.get_emoji_stats(),
                'words': day_analyzer.get_word_stats(top_n=30),  # Топ 30 слов для дня
                'activity': day_analyzer.get_activity_stats(),
                'message_length': day_analyzer.get_message_length_stats(),
                'messages': [
                    {
                        'datetime': msg['datetime'].isoformat(),
                        'date': msg['date'].isoformat(),
                        'time': msg['time'].isoformat(),
                        'hour': msg['hour'],
                        'author': msg['author'],
                        'text': msg['text'],
                    }
                    for msg in day_messages
                ],
                'first_message_time': min(msg['datetime'] for msg in day_messages).time().isoformat(),
                'last_message_time': max(msg['datetime'] for msg in day_messages).time().isoformat(),
            }
            
            return analysis
            
        except Exception as e:
            return {'error': f'Ошибка анализа дня: {str(e)}'}
    
    def get_ghosting_stats(self) -> Dict:
        """Анализ 'ghosting' - когда участники долго не отвечают"""
        if len(self.messages) < 2:
            return {'ghosting_events': []}
        
        ghosting_events = []
        authors = set(msg['author'] for msg in self.messages)
        
        # Для каждой пары участников находим периоды молчания
        for author in authors:
            last_message_time = None
            last_message_author = None
            
            for msg in self.messages:
                current_time = msg['datetime']
                
                if last_message_time and last_message_author and last_message_author != author:
                    # Вычисляем время между сообщениями
                    time_diff = (current_time - last_message_time).total_seconds() / 3600  # в часах
                    
                    # Если прошло больше 24 часов - это ghosting
                    if time_diff > 24:
                        ghosting_events.append({
                            'ghosted_by': last_message_author,
                            'ghosted_from': last_message_time.isoformat(),
                            'responded_by': author,
                            'responded_at': current_time.isoformat(),
                            'hours_silent': round(time_diff, 1),
                            'days_silent': round(time_diff / 24, 1),
                        })
                
                last_message_time = current_time
                last_message_author = msg['author']
        
        # Сортируем по длительности молчания
        ghosting_events.sort(key=lambda x: x['hours_silent'], reverse=True)
        
        # Статистика по участникам
        author_ghosting = defaultdict(lambda: {'count': 0, 'total_hours': 0, 'max_hours': 0})
        for event in ghosting_events:
            author = event['ghosted_by']
            author_ghosting[author]['count'] += 1
            author_ghosting[author]['total_hours'] += event['hours_silent']
            author_ghosting[author]['max_hours'] = max(author_ghosting[author]['max_hours'], event['hours_silent'])
        
        return {
            'total_ghosting_events': len(ghosting_events),
            'top_ghosting_events': ghosting_events[:20],  # Топ 20 самых долгих
            'author_stats': {
                author: {
                    'ghosting_count': stats['count'],
                    'avg_hours_silent': round(stats['total_hours'] / stats['count'], 1) if stats['count'] > 0 else 0,
                    'max_hours_silent': round(stats['max_hours'], 1),
                }
                for author, stats in author_ghosting.items()
            }
        }
    
    def get_activity_heatmap(self) -> Dict:
        """Тепловая карта активности по дням недели и часам"""
        # Создаем матрицу: день недели (0-6) x час (0-23)
        heatmap = defaultdict(lambda: defaultdict(int))
        
        # Также по датам для визуализации по календарю
        date_activity = defaultdict(int)
        
        for msg in self.messages:
            weekday = msg['weekday']
            hour = msg['hour']
            date = msg['date'].isoformat()
            
            heatmap[weekday][hour] += 1
            date_activity[date] += 1
        
        # Преобразуем в список для удобства
        weekday_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        heatmap_data = []
        
        for weekday in range(7):
            weekday_data = []
            for hour in range(24):
                count = heatmap[weekday][hour]
                weekday_data.append({
                    'hour': hour,
                    'count': count,
                })
            heatmap_data.append({
                'weekday': weekday,
                'weekday_name': weekday_names[weekday],
                'hours': weekday_data,
            })
        
        # Находим самые активные периоды
        max_activity = 0
        most_active_periods = []
        
        for weekday in range(7):
            for hour in range(24):
                count = heatmap[weekday][hour]
                if count > max_activity:
                    max_activity = count
                    most_active_periods = [{'weekday': weekday_names[weekday], 'hour': hour, 'count': count}]
                elif count == max_activity and count > 0:
                    most_active_periods.append({'weekday': weekday_names[weekday], 'hour': hour, 'count': count})
        
        return {
            'heatmap': heatmap_data,
            'date_activity': dict(date_activity),
            'max_activity': max_activity,
            'most_active_periods': most_active_periods[:10],  # Топ 10
        }
    
    def get_semantic_analysis(self) -> Dict:
        """Семантический анализ: темы, тональность, ключевые фразы"""
        if not self.messages:
            return {}
        
        # Анализ длины сообщений (индикатор тональности)
        short_messages = 0  # < 10 символов
        medium_messages = 0  # 10-50 символов
        long_messages = 0  # > 50 символов
        
        # Анализ использования вопросительных знаков
        question_messages = 0
        exclamation_messages = 0
        
        # Ключевые слова для определения тем
        topic_keywords = {
            'работа': ['работа', 'проект', 'задача', 'дедлайн', 'встреча', 'офис', 'коллега'],
            'личное': ['дом', 'семья', 'друзья', 'выходные', 'отпуск', 'праздник'],
            'планы': ['встреча', 'встретимся', 'планы', 'когда', 'где', 'время'],
            'вопросы': ['как', 'что', 'почему', 'когда', 'где', 'кто'],
            'эмоции': ['спасибо', 'извини', 'люблю', 'нравится', 'не нравится', 'грустно', 'радостно'],
        }
        
        topic_counts = defaultdict(int)
        
        for msg in self.messages:
            text = msg['text'].lower()
            length = len(text)
            
            # Длина
            if length < 10:
                short_messages += 1
            elif length < 50:
                medium_messages += 1
            else:
                long_messages += 1
            
            # Вопросы и восклицания
            if '?' in text:
                question_messages += 1
            if '!' in text:
                exclamation_messages += 1
            
            # Темы
            for topic, keywords in topic_keywords.items():
                if any(keyword in text for keyword in keywords):
                    topic_counts[topic] += 1
        
        total = len(self.messages)
        
        # Анализ активности по времени суток (утро/день/вечер/ночь)
        time_periods = {
            'утро': 0,  # 6-12
            'день': 0,  # 12-18
            'вечер': 0,  # 18-24
            'ночь': 0,  # 0-6
        }
        
        for msg in self.messages:
            hour = msg['hour']
            if 6 <= hour < 12:
                time_periods['утро'] += 1
            elif 12 <= hour < 18:
                time_periods['день'] += 1
            elif 18 <= hour < 24:
                time_periods['вечер'] += 1
            else:
                time_periods['ночь'] += 1
        
        return {
            'message_length_distribution': {
                'short': short_messages,
                'medium': medium_messages,
                'long': long_messages,
                'short_percentage': round(short_messages / total * 100, 1) if total > 0 else 0,
                'medium_percentage': round(medium_messages / total * 100, 1) if total > 0 else 0,
                'long_percentage': round(long_messages / total * 100, 1) if total > 0 else 0,
            },
            'communication_style': {
                'question_messages': question_messages,
                'exclamation_messages': exclamation_messages,
                'question_percentage': round(question_messages / total * 100, 1) if total > 0 else 0,
                'exclamation_percentage': round(exclamation_messages / total * 100, 1) if total > 0 else 0,
            },
            'topics': dict(sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)),
            'time_periods': time_periods,
            'time_periods_percentage': {
                period: round(count / total * 100, 1) if total > 0 else 0
                for period, count in time_periods.items()
            },
        }
    
    def get_message_series_stats(self) -> Dict:
        """Анализ серий сообщений - кто пишет залпами"""
        if len(self.messages) < 2:
            return {}
        
        series_threshold = 300  # 5 минут в секундах
        author_series = defaultdict(lambda: {'total_series': 0, 'total_messages_in_series': 0, 'series_lengths': []})
        
        current_series = []
        current_author = None
        last_time = None
        
        for msg in self.messages:
            current_time = msg['datetime']
            
            if last_time is None:
                current_series = [msg]
                current_author = msg['author']
                last_time = current_time
                continue
            
            time_diff = (current_time - last_time).total_seconds()
            
            # Если тот же автор и прошло меньше порога - продолжаем серию
            if msg['author'] == current_author and time_diff < series_threshold:
                current_series.append(msg)
            else:
                # Завершаем предыдущую серию
                if len(current_series) >= 3:  # Серия от 3 сообщений
                    author_series[current_author]['total_series'] += 1
                    author_series[current_author]['total_messages_in_series'] += len(current_series)
                    author_series[current_author]['series_lengths'].append(len(current_series))
                
                # Начинаем новую серию
                current_series = [msg]
                current_author = msg['author']
            
            last_time = current_time
        
        # Обрабатываем последнюю серию
        if len(current_series) >= 3:
            author_series[current_author]['total_series'] += 1
            author_series[current_author]['total_messages_in_series'] += len(current_series)
            author_series[current_author]['series_lengths'].append(len(current_series))
        
        # Формируем результат
        result = {}
        for author, stats in author_series.items():
            avg_length = sum(stats['series_lengths']) / len(stats['series_lengths']) if stats['series_lengths'] else 0
            max_length = max(stats['series_lengths']) if stats['series_lengths'] else 0
            result[author] = {
                'total_series': stats['total_series'],
                'total_messages_in_series': stats['total_messages_in_series'],
                'avg_series_length': round(avg_length, 1),
                'max_series_length': max_length,
                'series_distribution': {
                    '3-5': len([s for s in stats['series_lengths'] if 3 <= s <= 5]),
                    '6-10': len([s for s in stats['series_lengths'] if 6 <= s <= 10]),
                    '11-20': len([s for s in stats['series_lengths'] if 11 <= s <= 20]),
                    '20+': len([s for s in stats['series_lengths'] if s > 20]),
                }
            }
        
        return {'author_series': result}
    
    def get_reaction_speed_stats(self) -> Dict:
        """Анализ скорости реакции участников"""
        if len(self.messages) < 2:
            return {}
        
        author_response_times = defaultdict(list)
        author_response_distribution = defaultdict(lambda: {'under_5min': 0, 'under_1hour': 0, 'under_1day': 0, 'over_1day': 0})
        conversation_starters = defaultdict(int)
        
        last_message_time = None
        last_author = None
        last_other_authors = set()
        
        for msg in self.messages:
            current_time = msg['datetime']
            current_author = msg['author']
            
            if last_message_time:
                time_diff = (current_time - last_message_time).total_seconds()
                hours_diff = time_diff / 3600
                
                # Если это ответ другому участнику (не самому себе)
                if current_author != last_author and current_author in last_other_authors:
                    minutes = time_diff / 60
                    author_response_times[current_author].append(minutes)
                    
                    # Распределение по времени
                    if minutes < 5:
                        author_response_distribution[current_author]['under_5min'] += 1
                    elif hours_diff < 1:
                        author_response_distribution[current_author]['under_1hour'] += 1
                    elif hours_diff < 24:
                        author_response_distribution[current_author]['under_1day'] += 1
                    else:
                        author_response_distribution[current_author]['over_1day'] += 1
                
                # Инициатор диалога после паузы (более 6 часов)
                if hours_diff > 6:
                    conversation_starters[current_author] += 1
            
            # Обновляем информацию о последних участниках
            if last_author:
                last_other_authors.add(last_author)
            
            last_message_time = current_time
            last_author = current_author
        
        # Вычисляем средние времена ответа
        author_avg_response = {}
        for author, times in author_response_times.items():
            if times:
                author_avg_response[author] = {
                    'avg_minutes': round(sum(times) / len(times), 1),
                    'median_minutes': round(sorted(times)[len(times) // 2], 1),
                    'total_responses': len(times),
                }
        
        return {
            'avg_response_times': author_avg_response,
            'response_distribution': dict(author_response_distribution),
            'conversation_starters': dict(conversation_starters),
        }
    
    def get_participant_balance(self) -> Dict:
        """Баланс и вклад участников"""
        if not self.messages:
            return {}
        
        author_stats = defaultdict(lambda: {
            'messages': 0,
            'words': 0,
            'characters': 0,
            'questions': 0,
            'statements': 0,
        })
        
        total_messages = len(self.messages)
        total_words = 0
        total_chars = 0
        
        for msg in self.messages:
            author = msg['author']
            text = msg['text']
            
            author_stats[author]['messages'] += 1
            words = len(text.split())
            chars = len(text)
            
            author_stats[author]['words'] += words
            author_stats[author]['characters'] += chars
            total_words += words
            total_chars += chars
            
            # Вопросы и утверждения
            if '?' in text:
                author_stats[author]['questions'] += 1
            else:
                author_stats[author]['statements'] += 1
        
        result = {}
        for author, stats in author_stats.items():
            result[author] = {
                'message_percentage': round(stats['messages'] / total_messages * 100, 1) if total_messages > 0 else 0,
                'word_percentage': round(stats['words'] / total_words * 100, 1) if total_words > 0 else 0,
                'character_percentage': round(stats['characters'] / total_chars * 100, 1) if total_chars > 0 else 0,
                'questions_count': stats['questions'],
                'statements_count': stats['statements'],
                'question_ratio': round(stats['questions'] / stats['messages'] * 100, 1) if stats['messages'] > 0 else 0,
            }
        
        return {'participants': result}
    
    def get_emotional_analysis(self) -> Dict:
        """Эмоциональный анализ"""
        if not self.messages:
            return {}
        
        # Эмоциональные словари (упрощенные)
        positive_words = ['спасибо', 'отлично', 'хорошо', 'класс', 'супер', 'рад', 'радость', 'люблю', 'нравится', 'круто']
        negative_words = ['плохо', 'ужасно', 'ненавижу', 'злой', 'злюсь', 'грустно', 'печаль', 'проблема', 'ошибка', 'неправильно']
        anxiety_words = ['беспокоюсь', 'волнуюсь', 'тревога', 'страх', 'боюсь', 'переживаю', 'нервничаю']
        
        daily_emotions = defaultdict(lambda: {'positive': 0, 'negative': 0, 'anxiety': 0, 'total': 0})
        topic_emotions = defaultdict(lambda: {'positive': 0, 'negative': 0, 'anxiety': 0})
        
        for msg in self.messages:
            text = msg['text'].lower()
            date = msg['date'].isoformat()
            
            daily_emotions[date]['total'] += 1
            
            # Проверяем эмоциональные слова
            pos_count = sum(1 for word in positive_words if word in text)
            neg_count = sum(1 for word in negative_words if word in text)
            anx_count = sum(1 for word in anxiety_words if word in text)
            
            if pos_count > 0:
                daily_emotions[date]['positive'] += 1
            if neg_count > 0:
                daily_emotions[date]['negative'] += 1
            if anx_count > 0:
                daily_emotions[date]['anxiety'] += 1
            
            # Простая тематика для эмоций
            if any(word in text for word in ['работа', 'проект', 'задача']):
                if pos_count > 0:
                    topic_emotions['работа']['positive'] += 1
                if neg_count > 0:
                    topic_emotions['работа']['negative'] += 1
            if any(word in text for word in ['встреча', 'планы', 'время']):
                if anx_count > 0:
                    topic_emotions['планы']['anxiety'] += 1
        
        # Находим дни с высокой негативностью
        tense_days = []
        for date, emotions in daily_emotions.items():
            if emotions['total'] > 0:
                neg_ratio = emotions['negative'] / emotions['total']
                if neg_ratio > 0.3:  # Более 30% негатива
                    tense_days.append({
                        'date': date,
                        'negative_ratio': round(neg_ratio * 100, 1),
                        'total_messages': emotions['total'],
                    })
        
        tense_days.sort(key=lambda x: x['negative_ratio'], reverse=True)
        
        return {
            'daily_emotions': dict(daily_emotions),
            'topic_emotions': dict(topic_emotions),
            'tense_days': tense_days[:20],
        }
    
    def get_communication_style(self) -> Dict:
        """Стиль общения"""
        if not self.messages:
            return {}
        
        author_styles = defaultdict(lambda: {
            'formal': 0,  # "вы", обращения
            'informal': 0,  # "ты", сленг
            'emojis_count': 0,
            'caps_count': 0,
            'ellipsis_count': 0,
            'exclamation_count': 0,
            'unique_words': set(),
            'total_words': 0,
            'parasite_words': defaultdict(int),
        })
        
        parasite_words_list = ['типа', 'как бы', 'в общем', 'короче', 'ну', 'это', 'вот', 'так']
        
        for msg in self.messages:
            author = msg['author']
            text = msg['text']
            text_lower = text.lower()
            
            # Формальность
            if any(word in text_lower for word in ['вы', 'вас', 'вам', 'ваш']):
                author_styles[author]['formal'] += 1
            if any(word in text_lower for word in ['ты', 'тебя', 'тебе', 'твой']):
                author_styles[author]['informal'] += 1
            
            # Эмодзи
            emoji_count = len([char for char in text if char in emoji.EMOJI_DATA])
            author_styles[author]['emojis_count'] += emoji_count
            
            # Капс
            if text.isupper() and len(text) > 3:
                author_styles[author]['caps_count'] += 1
            
            # Многоточия
            author_styles[author]['ellipsis_count'] += text.count('...')
            
            # Восклицания
            author_styles[author]['exclamation_count'] += text.count('!')
            
            # Уникальные слова
            words = re.findall(r'\b\w+\b', text_lower)
            author_styles[author]['unique_words'].update(words)
            author_styles[author]['total_words'] += len(words)
            
            # Паразитные слова
            for parasite in parasite_words_list:
                if parasite in text_lower:
                    author_styles[author]['parasite_words'][parasite] += 1
        
        result = {}
        for author, style in author_styles.items():
            total_messages = sum([style['formal'], style['informal']]) if (style['formal'] + style['informal']) > 0 else 1
            result[author] = {
                'formality_ratio': round(style['formal'] / total_messages * 100, 1) if total_messages > 0 else 0,
                'emojis_per_message': round(style['emojis_count'] / total_messages, 1) if total_messages > 0 else 0,
                'caps_usage': style['caps_count'],
                'ellipsis_usage': style['ellipsis_count'],
                'exclamation_usage': style['exclamation_count'],
                'lexical_diversity': round(len(style['unique_words']) / style['total_words'] * 100, 1) if style['total_words'] > 0 else 0,
                'top_parasite_words': dict(sorted(style['parasite_words'].items(), key=lambda x: x[1], reverse=True)[:5]),
            }
        
        return {'author_styles': result}
    
    def get_conflict_analysis(self) -> Dict:
        """Анализ конфликтов и маркерных фраз"""
        if not self.messages:
            return {}
        
        marker_phrases = {
            'resolution': ['ладно', 'ок', 'окей', 'понятно', 'хорошо', 'согласен', 'принято'],
            'tension': ['как хочешь', 'делай что хочешь', 'не важно', 'без разницы', 'неважно'],
            'apology': ['извини', 'извините', 'прости', 'простите', 'сорри'],
            'compromise': ['может', 'возможно', 'попробуем', 'давай попробуем', 'давайте'],
        }
        
        phrase_usage = defaultdict(lambda: defaultdict(int))
        author_apologies = defaultdict(int)
        author_compromises = defaultdict(int)
        
        for msg in self.messages:
            text_lower = msg['text'].lower()
            author = msg['author']
            
            for category, phrases in marker_phrases.items():
                for phrase in phrases:
                    if phrase in text_lower:
                        phrase_usage[category][phrase] += 1
                        if category == 'apology':
                            author_apologies[author] += 1
                        elif category == 'compromise':
                            author_compromises[author] += 1
        
        return {
            'marker_phrases': {cat: dict(sorted(phrases.items(), key=lambda x: x[1], reverse=True)) 
                              for cat, phrases in phrase_usage.items()},
            'apology_stats': dict(author_apologies),
            'compromise_stats': dict(author_compromises),
        }
    
    def get_seasonality_analysis(self) -> Dict:
        """Сезонность и динамика активности"""
        if not self.messages:
            return {}
        
        weekly_activity = defaultdict(int)
        monthly_activity = defaultdict(int)
        
        for msg in self.messages:
            # Неделя года
            week = msg['datetime'].strftime('%Y-W%V')
            weekly_activity[week] += 1
            
            # Месяц
            month = msg['datetime'].strftime('%Y-%m')
            monthly_activity[month] += 1
        
        # Находим пики
        if weekly_activity:
            max_week = max(weekly_activity.items(), key=lambda x: x[1])
            min_week = min(weekly_activity.items(), key=lambda x: x[1])
        else:
            max_week = min_week = (None, 0)
        
        if monthly_activity:
            max_month = max(monthly_activity.items(), key=lambda x: x[1])
            min_month = min(monthly_activity.items(), key=lambda x: x[1])
        else:
            max_month = min_month = (None, 0)
        
        return {
            'weekly_activity': dict(sorted(weekly_activity.items())),
            'monthly_activity': dict(sorted(monthly_activity.items())),
            'peaks': {
                'max_week': {'period': max_week[0], 'messages': max_week[1]},
                'min_week': {'period': min_week[0], 'messages': min_week[1]},
                'max_month': {'period': max_month[0], 'messages': max_month[1]},
                'min_month': {'period': min_month[0], 'messages': min_month[1]},
            }
        }
    
    def get_full_analysis(self) -> Dict:
        """Полный анализ чата"""
        return {
            'basic': self.get_basic_stats(),
            'emoji': self.get_emoji_stats(),
            'words': self.get_word_stats(),
            'activity': self.get_activity_stats(),
            'message_length': self.get_message_length_stats(),
            'interesting': self.get_interesting_stats(),
            'ghosting': self.get_ghosting_stats(),
            'activity_heatmap': self.get_activity_heatmap(),
            'semantic': self.get_semantic_analysis(),
            'message_series': self.get_message_series_stats(),
            'reaction_speed': self.get_reaction_speed_stats(),
            'participant_balance': self.get_participant_balance(),
            'emotional': self.get_emotional_analysis(),
            'communication_style': self.get_communication_style(),
            'conflict': self.get_conflict_analysis(),
            'seasonality': self.get_seasonality_analysis(),
        }

