from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/get-subtitles', methods=['POST'])
def get_subtitles():
    # Получаем URL видео и язык из запроса
    data = request.get_json()
    video_url = data.get('url')
    lang = data.get('lang', 'ru')  # По умолчанию русский

    if not video_url:
        return jsonify({"error": "URL is required"}), 400

    # Имя файла для субтитров
    output_file = "subtitles"
    
    # Команда yt-dlp для скачивания субтитров
    command = [
        "yt-dlp",
        "--skip-download",        # Не скачивать видео
        "--write-auto-sub",      # Скачивать автоматические субтитры
        "--sub-lang", lang,      # Язык субтитров
        "--output", output_file, # Имя выходного файла
        video_url
    ]
    
    try:
        # Выполняем команду
        subprocess.run(command, check=True)
        
        # Читаем субтитры из файла
        subtitle_file = f"{output_file}.{lang}.vtt"  # yt-dlp создает файл с языковым суффиксом
        if not os.path.exists(subtitle_file):
            return jsonify({"error": "Subtitles not found"}), 404
        
        with open(subtitle_file, 'r', encoding='utf-8') as f:
            subtitles = f.read()
        
        # Удаляем временный файл
        os.remove(subtitle_file)
        
        return jsonify({"subtitles": subtitles})
    
    except subprocess.CalledProcessError as e:
        return jsonify({"error": "Failed to download subtitles", "details": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway использует переменную PORT
    app.run(host="0.0.0.0", port=port)
