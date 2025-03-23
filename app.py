from flask import Flask, request, jsonify
import subprocess
import os
import logging
import re

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/get-subtitles', methods=['POST'])
def get_subtitles():
    logger.debug("Received request to /get-subtitles")
    
    # Получаем URL видео и язык из запроса
    data = request.get_json()
    video_url = data.get('url')
    lang = data.get('lang', 'ru')  # По умолчанию русский

    if not video_url:
        logger.error("URL is required")
        return jsonify({"error": "URL is required"}), 400

    # Имя файла для субтитров
    output_file = "/tmp/subtitles"
    
    # Создаем cookies.txt из переменной окружения COOKIES
    cookies_content = os.getenv("COOKIES")
    cookies_file = "/tmp/cookies.txt"
    if cookies_content:
        with open(cookies_file, "w") as f:
            f.write(cookies_content)
        logger.debug(f"Created cookies file: {cookies_file}")
    else:
        logger.warning("COOKIES environment variable not found, proceeding without cookies")
        cookies_file = None

    # Команда yt-dlp для скачивания субтитров
    command = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-sub",
        "--sub-lang", lang,
        "--sub-format", "srt",  # Скачиваем в формате .srt
        "--convert-subs", "srt",  # Убедимся, что субтитры в .srt
    ]
    if cookies_file:
        command.extend(["--cookies", cookies_file])
    command.extend(["--output", output_file, video_url])
    
    logger.debug(f"Executing command: {' '.join(command)}")
    
    try:
        # Выполняем команду
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logger.debug(f"yt-dlp output: {result.stdout}")
        logger.debug(f"yt-dlp stderr: {result.stderr}")
        
        # Читаем субтитры из файла
        subtitle_file = f"{output_file}.{lang}.srt"
        if not os.path.exists(subtitle_file):
            logger.error(f"Subtitle file not found: {subtitle_file}")
            return jsonify({"error": "Subtitles not found"}), 404

        # Читаем .srt файл и извлекаем текст
        with open(subtitle_file, 'r', encoding='utf-8') as f:
            srt_content = f.read()

        # Парсим .srt и извлекаем чистый текст
        # Удаляем таймкоды, номера строк и пустые строки
        lines = srt_content.split('\n')
        clean_text = []
        for line in lines:
            # Пропускаем пустые строки, номера и таймкоды
            if not line.strip():
                continue
            if line.isdigit():
                continue
            if '-->' in line:
                continue
            clean_text.append(line.strip())

        # Объединяем строки в текст
        subtitles_text = ' '.join(clean_text)

        logger.debug(f"Cleaned subtitles text: {subtitles_text[:100]}...")
        
        # Удаляем временные файлы
        os.remove(subtitle_file)
        if cookies_file and os.path.exists(cookies_file):
            os.remove(cookies_file)
        logger.debug(f"Deleted temporary files")
        
        return jsonify({"subtitles": subtitles_text})
    
    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp failed: {e}")
        logger.error(f"yt-dlp stderr: {e.stderr}")
        return jsonify({"error": "Failed to download subtitles", "details": str(e), "stderr": e.stderr}), 500
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        return jsonify({"error": "Server error", "details": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
