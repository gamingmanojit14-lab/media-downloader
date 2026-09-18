from flask import Flask, render_template, request, jsonify, send_file
import subprocess
import os
import threading
import re
import requests
from urllib.parse import urlparse

app = Flask(__name__)

# Ekhon file ta project folder e save hobe, browser e pathanor jonno
DOWNLOAD_DIR = os.path.join(os.getcwd(), "temp_downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

download_status = {
    "is_downloading": False,
    "progress": 0,
    "speed": "",
    "eta": "",
    "message": "",
    "site": "",
    "filename": "",
    "success": False
}

SUPPORTED_SITES = {
    "youtube.com": "YouTube", "youtu.be": "YouTube",
    "facebook.com": "Facebook", "fb.watch": "Facebook",
    "instagram.com": "Instagram",
    "tiktok.com": "TikTok",
    "twitter.com": "Twitter", "x.com": "Twitter",
    "vimeo.com": "Vimeo", "dailymotion.com": "Dailymotion",
    "reddit.com": "Reddit", "pinterest.com": "Pinterest",
    "linkedin.com": "LinkedIn", "twitch.tv": "Twitch",
    "soundcloud.com": "SoundCloud",
}

def detect_site(url):
    domain = urlparse(url).netloc.lower().replace("www.", "")
    for site, name in SUPPORTED_SITES.items():
        if site in domain:
            return name
    return "Generic / Direct Link"

def is_direct_video(url):
    direct_extensions = ['.mp4', '.mkv', '.webm', '.mov', '.avi', '.flv', '.m3u8', '.mp3', '.m4a', '.wav']
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in direct_extensions)

def download_direct_video(url):
    global download_status
    try:
        filename = os.path.basename(urlparse(url).path) or "video.mp4"
        if not any(filename.endswith(ext) for ext in ['.mp4', '.mkv', '.webm', '.mp3', '.m4a']):
            filename += ".mp4"
        
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        with requests.get(url, stream=True, headers=headers, timeout=30) as r:
            r.raise_for_status()
            total = int(r.headers.get('content-length', 0))
            downloaded = 0
            start_time = __import__('time').time()
            
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            download_status["progress"] = round((downloaded / total) * 100, 1)
                            elapsed = __import__('time').time() - start_time
                            if elapsed > 0:
                                speed = downloaded / elapsed / 1024 / 1024
                                download_status["speed"] = f"{speed:.2f} MB/s"
                                if speed > 0:
                                    remaining = (total - downloaded) / (speed * 1024 * 1024)
                                    download_status["eta"] = f"{int(remaining)}s"
                            download_status["filename"] = filename
        
        download_status["message"] = f"✅ Server download shesh! Ekhon browser e pathano hocche..."
        download_status["success"] = True
    except Exception as e:
        download_status["message"] = f"❌ Direct download fail: {str(e)[:200]}"
    finally:
        download_status["is_downloading"] = False

def run_ytdlp_download(url, media_type, quality):
    global download_status
    output_template = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
    
    if media_type == 'mp3':
        cmd = ["yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "0",
               "--newline", "--progress-template", "%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
               "-o", output_template, url]
    else:
        cmd = ["yt-dlp", "-f", f"bv*[height<={quality}]+ba/best",
               "--merge-output-format", "mp4", "--newline",
               "--progress-template", "%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
               "-o", output_template, url]
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        
        for line in process.stdout:
            line = line.strip()
            if '|' in line and '%' in line:
                try:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        download_status["progress"] = float(parts[0].replace('%', '').strip())
                        download_status["speed"] = parts[1].strip()
                        download_status["eta"] = parts[2].strip()
                except: pass
            elif "[download] Destination:" in line:
                fname = line.split("Destination:")[-1].strip()
                download_status["filename"] = os.path.basename(fname)
            elif "has already been downloaded" in line:
                fname = line.split("has already been downloaded")[0].replace("[download]", "").strip()
                download_status["filename"] = os.path.basename(fname)
        
        process.wait()
        
        if process.returncode == 0:
            download_status["message"] = "✅ Server download shesh! Ekhon browser e pathano hocche..."
            download_status["success"] = True
        else:
            download_status["message"] = "❌ Download fail! Link ta check koro."
    except Exception as e:
        download_status["message"] = f"❌ Error: {str(e)[:200]}"
    finally:
        download_status["is_downloading"] = False

def run_download(url, media_type, quality):
    global download_status
    download_status.update({"is_downloading": True, "progress": 0, "speed": "", "eta": "", "filename": "", "success": False})
    
    site = detect_site(url)
    download_status["site"] = site
    download_status["message"] = f"⏳ {site} theke download shuru hocche..."
    
    if is_direct_video(url) and site == "Generic / Direct Link":
        download_direct_video(url)
    else:
        run_ytdlp_download(url, media_type, quality)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/detect', methods=['POST'])
def detect():
    data = request.json
    url = data.get('url', '').strip()
    if not url.startswith(("http://", "https://")):
        return jsonify({'error': 'Valid URL dao'}), 400
    site = detect_site(url)
    is_direct = is_direct_video(url)
    return jsonify({'site': site, 'is_direct': is_direct, 'method': 'Direct Download' if (is_direct and site == "Generic / Direct Link") else 'yt-dlp Engine'})

@app.route('/api/download', methods=['POST'])
def download():
    global download_status
    if download_status["is_downloading"]:
        return jsonify({'error': 'Ekta download already cholche!'}), 400
    data = request.json
    url = data.get('url', '').strip()
    if not url.startswith(("http://", "https://")):
        return jsonify({'error': 'Valid link dao!'}), 400
    thread = threading.Thread(target=run_download, args=(url, data.get('type', 'mp4'), data.get('quality', '720')))
    thread.start()
    return jsonify({'success': True, 'message': 'Download shuru hoyeche...'})

@app.route('/api/status')
def status():
    return jsonify(download_status)

# Ekhon notun route, jeta browser ke file ta pathiye debe
@app.route('/api/get_file/<path:filename>')
def get_file(filename):
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return "File pawa jay nai", 404

if __name__ == '__main__':
    print("🚀 Universal Media Downloader chalu hocche...")
    print("📱 Browser e open koro: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
