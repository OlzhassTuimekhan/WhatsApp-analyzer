from flask import Flask, render_template, jsonify, request
from chat_parser import ChatParser, ChatAnalyzer
from chat_ai import ChatAnalyzerAI
import os
import uuid
from werkzeug.utils import secure_filename

# Определяем путь к директории с шаблонами
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)

# Директория для загруженных файлов
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Текущий активный файл (None если файл не загружен)
_current_chat_file = None

# Кэш для результатов анализа
_analysis_cache = None
_analyzer_instance = None
_messages_cache = None

def get_current_chat_file():
    """Получает путь к текущему активному файлу чата"""
    global _current_chat_file
    return _current_chat_file

def get_analysis():
    """Получает анализ чата (с кэшированием)"""
    global _analysis_cache, _analyzer_instance, _messages_cache
    
    chat_file = get_current_chat_file()
    
    if chat_file is None:
        return {'error': 'Файл не загружен. Пожалуйста, загрузите файл чата.'}
    
    if not os.path.exists(chat_file):
        return {'error': f'Файл {chat_file} не найден. Пожалуйста, загрузите файл заново.'}
    
    if _analysis_cache is None:
        # Парсим чат
        parser = ChatParser(chat_file)
        messages = parser.parse()
        _messages_cache = messages
        
        # Анализируем
        analyzer = ChatAnalyzer(messages)
        _analyzer_instance = analyzer
        _analysis_cache = analyzer.get_full_analysis()
    
    return _analysis_cache

def get_analyzer():
    """Получает экземпляр анализатора (для поиска)"""
    global _analyzer_instance, _messages_cache
    
    chat_file = get_current_chat_file()
    
    if chat_file is None:
        raise ValueError('Файл не загружен. Пожалуйста, загрузите файл чата.')
    
    if not os.path.exists(chat_file):
        raise ValueError(f'Файл {chat_file} не найден. Пожалуйста, загрузите файл заново.')
    
    if _analyzer_instance is None:
        # Парсим чат
        parser = ChatParser(chat_file)
        messages = parser.parse()
        _messages_cache = messages
        
        # Создаем анализатор
        analyzer = ChatAnalyzer(messages)
        _analyzer_instance = analyzer
    
    return _analyzer_instance

def clear_cache():
    """Очищает кэш анализа"""
    global _analysis_cache, _analyzer_instance, _messages_cache
    _analysis_cache = None
    _analyzer_instance = None
    _messages_cache = None

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/chat')
def chat():
    """Страница чата с AI"""
    return render_template('chat.html')

@app.route('/api/analysis')
def get_full_analysis():
    """API endpoint для получения полного анализа"""
    try:
        analysis = get_analysis()
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/refresh')
def refresh_analysis():
    """Обновить кэш анализа"""
    clear_cache()
    try:
        analysis = get_analysis()
        return jsonify({'status': 'success', 'analysis': analysis})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Загрузка файла чата"""
    global _current_chat_file
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не выбран'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        # Сохраняем файл
        filename = secure_filename(file.filename)
        # Добавляем уникальный ID чтобы не перезаписывать
        unique_id = str(uuid.uuid4())[:8]
        saved_filename = f"{unique_id}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, saved_filename)
        file.save(filepath)
        
        # Переключаемся на загруженный файл
        _current_chat_file = filepath
        
        # Очищаем кэш
        clear_cache()
        
        return jsonify({
            'status': 'success',
            'filename': filename,
            'message': 'Файл успешно загружен'
        })
    except OSError as e:
        if e.errno == 28:  # No space left on device
            return jsonify({'error': 'Недостаточно места на диске для загрузки файла. Освободите место и попробуйте снова.'}), 507
        return jsonify({'error': f'Ошибка файловой системы: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Ошибка загрузки файла: {str(e)}'}), 500


@app.route('/api/current_file')
def get_current_file():
    """Получить информацию о текущем файле"""
    global _current_chat_file
    
    if _current_chat_file is None:
        return jsonify({
            'current_file': None,
            'is_loaded': False,
            'filename': 'Файл не загружен'
        })
    
    filename = os.path.basename(_current_chat_file)
    
    return jsonify({
        'current_file': _current_chat_file,
        'is_loaded': True,
        'filename': filename
    })

@app.route('/api/search')
def search_word():
    """API endpoint для поиска слова"""
    word = request.args.get('word', '').strip()
    case_sensitive = request.args.get('case_sensitive', 'false').lower() == 'true'
    
    if not word:
        return jsonify({'error': 'Слово не указано'}), 400
    
    try:
        analyzer = get_analyzer()
        results = analyzer.search_word(word, case_sensitive=case_sensitive)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/context')
def get_context():
    """API endpoint для получения контекста сообщения"""
    datetime_str = request.args.get('datetime', '').strip()
    context_size = int(request.args.get('context_size', 10))
    
    if not datetime_str:
        return jsonify({'error': 'Дата и время не указаны'}), 400
    
    try:
        analyzer = get_analyzer()
        context = analyzer.get_message_context(datetime_str, context_size)
        return jsonify(context)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/day_analysis')
def get_day_analysis():
    """API endpoint для получения анализа конкретного дня"""
    date_str = request.args.get('date', '').strip()
    
    if not date_str:
        return jsonify({'error': 'Дата не указана'}), 400
    
    try:
        analyzer = get_analyzer()
        analysis = analyzer.get_day_analysis(date_str)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/messages_by_hour')
def get_messages_by_hour():
    """API endpoint для получения сообщений за конкретный час"""
    hour_str = request.args.get('hour', '').strip()
    date_str = request.args.get('date', '').strip()
    
    if not hour_str:
        return jsonify({'error': 'Час не указан'}), 400
    
    try:
        hour = int(hour_str)
        if hour < 0 or hour > 23:
            return jsonify({'error': 'Неверный час (должен быть 0-23)'}), 400
        
        analyzer = get_analyzer()
        result = analyzer.get_messages_by_hour(hour, date_str if date_str else None)
        return jsonify(result)
    except ValueError:
        return jsonify({'error': 'Неверный формат часа'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/ask', methods=['POST'])
def ask_ai():
    """API endpoint для вопросов к AI о чате"""
    data = request.get_json()
    question = data.get('question', '').strip()
    api_key = data.get('api_key', '').strip()
    conversation_history = data.get('history', [])
    # Дата для анализа конкретного дня (может быть None или пустой строкой)
    date_value = data.get('date')
    date = date_value.strip() if date_value else ''
    
    if not question:
        return jsonify({'error': 'Вопрос не указан'}), 400
    
    if not api_key:
        return jsonify({'error': 'OpenAI API key не указан'}), 400
    
    try:
        # Получаем анализ
        analysis = get_analysis()
        if 'error' in analysis:
            return jsonify({'error': analysis['error']}), 400
        
        # Если указана дата, получаем анализ конкретного дня
        day_analysis = None
        if date:
            try:
                analyzer = get_analyzer()
                day_analysis = analyzer.get_day_analysis(date)
            except Exception as e:
                # Если не удалось получить анализ дня, продолжаем без него
                day_analysis = {'error': f'Не удалось получить анализ дня: {str(e)}'}
        
        # Получаем примеры сообщений
        messages_sample = []
        if _messages_cache:
            # Берем первые 50 и последние 50 сообщений для контекста
            total = len(_messages_cache)
            sample_size = min(50, total)
            
            first_messages = [
                {
                    'date': msg['date'].isoformat(),
                    'time': msg['time'].isoformat(),
                    'author': msg['author'],
                    'text': msg['text'],
                }
                for msg in _messages_cache[:sample_size]
            ]
            
            last_messages = []
            if total > sample_size:
                last_messages = [
                    {
                        'date': msg['date'].isoformat(),
                        'time': msg['time'].isoformat(),
                        'author': msg['author'],
                        'text': msg['text'],
                    }
                    for msg in _messages_cache[-sample_size:]
                ]
            
            messages_sample = first_messages + last_messages
        
        # Создаем AI клиент и задаем вопрос
        ai_client = ChatAnalyzerAI(api_key=api_key)
        answer = ai_client.ask_question(
            question, 
            analysis, 
            messages_sample=messages_sample,
            conversation_history=conversation_history,
            day_analysis=day_analysis
        )
        
        return jsonify({
            'answer': answer,
            'status': 'success'
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Ошибка: {str(e)}'}), 500

if __name__ == '__main__':
    # Создаем директорию для шаблонов, если её нет
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=1234)

