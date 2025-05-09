from flask import Flask, request, jsonify
import subprocess
import os
import logging
import re

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/get-subtitles', methods=['POST'])
def get_subtitles():
    logger.debug("Received request to /get-subtitles")

    data = request.get_json()
    video_url = data.get('url')
    lang = data.get('lang', 'ru')
    sub_format = data.get('format', 'vtt').lower()

    if sub_format not in ['vtt', 'srt', 'txt']:
        logger.error("Invalid format specified")
        return jsonify({"error": "Invalid format specified. Use 'vtt', 'srt', or 'txt'."}), 400

    if not video_url:
        logger.error("URL is required")
        return jsonify({"error": "URL is required"}), 400

    output_file = "/tmp/subtitles"

    cookies_content = os.getenv("COOKIES")
    cookies_file = "/tmp/cookies.txt"
    if cookies_content:
        with open(cookies_file, "w") as f:
            f.write(cookies_content)
        logger.debug(f"Created cookies file: {cookies_file}")
    else:
        logger.warning("COOKIES environment variable not found, proceeding without cookies")
        cookies_file = None

    command = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-sub",
        "--sub-lang", lang,
        "--sub-format", "vtt/srt",
    ]
    if cookies_file:
        command.extend(["--cookies", cookies_file])
    command.extend(["--output", output_file, video_url])

    logger.debug(f"Executing command: {' '.join(command)}")

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)

        subtitle_file_vtt = f"{output_file}.{lang}.vtt"
        subtitle_file_srt = f"{output_file}.{lang}.srt"

        subtitle_file = subtitle_file_vtt if os.path.exists(subtitle_file_vtt) else subtitle_file_srt
        if not os.path.exists(subtitle_file):
            logger.error(f"Subtitle file not found: {subtitle_file}")
            return jsonify({"error": "Subtitles not found"}), 404

        with open(subtitle_file, 'r', encoding='utf-8') as f:
            subtitles_content = f.read()

        if sub_format == 'txt':
            subtitles_content = re.sub(r'(WEBVTT.*?\n\n)|(\d{2}:\d{2}:\d{2}[\.,]\d{3} --> .*?\n)|(<.*?>)', '', subtitles_content, flags=re.DOTALL)
            subtitles_lines = subtitles_content.strip().split('\n')
            seen = set()
            subtitles_unique = []
            for line in subtitles_lines:
                line_clean = line.strip()
                if line_clean and line_clean not in seen:
                    seen.add(line_clean)
                    subtitles_unique.append(line_clean)
            subtitles = '\n'.join(subtitles_unique)
        else:
            subtitles = subtitles_content

        os.remove(subtitle_file)
        if cookies_file and os.path.exists(cookies_file):
            os.remove(cookies_file)
        logger.debug("Deleted temporary files")

        return jsonify({"subtitles": subtitles})

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
