from flask import Flask, request, jsonify
import subprocess
import os
import logging

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
    output_file = "/tmp/subtitles"  # Используем /tmp для временных файлов
    
    # Команда yt-dlp для скачивания субтитров
    command = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-sub",
        "--sub-lang", lang,
        "--sub-format", "vtt/srt",
        "--cookies", "cookies.txt",  # Добавляем cookies
        "--output", output_file,
        video_url
    ]
    
    logger.debug(f"Executing command: {' '.join(command)}")
    
    try:
        # Выполняем команду
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logger.debug(f"yt-dlp output: {result.stdout}")
        logger.debug(f"yt-dlp stderr: {result.stderr}")
        
        # Читаем субтитры из файла
        subtitle_file_vtt = f"{output_file}.{lang}.vtt"
        subtitle_file_srt = f"{output_file}.{lang}.srt"
        
        subtitle_file = None
        if os.path.exists(subtitle_file_vtt):
            subtitle_file = subtitle_file_vtt
        elif os.path.exists(subtitle_file_srt):
            subtitle_file = subtitle_file_srt
        else:
            logger.error(f"Subtitle file not found: {subtitle_file_vtt} or {subtitle_file_srt}")
            return jsonify({"error": "Subtitles not found"}), 404

        with open(subtitle_file, 'r', encoding='utf-8') as f:
            subtitles = f.read()
        
        logger.debug(f"Subtitles content: {subtitles[:100]}...")
        
        # Удаляем временный файл
        os.remove(subtitle_file)
        logger.debug(f"Deleted subtitle file: {subtitle_file}")
        
        return jsonify({"subtitles": subtitles})
    
    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp failed: {e}")
        logger.error(f"yt-dlp stderr: {e.stderr}")
        return jsonify({"error": "Failed to download subtitles", "details": str(e), "stderr": e.stderr}), 500
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        return jsonify({"error": "Server error", "details": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway использует переменную PORT
    app.run(host="0.0.0.0", port=port)
