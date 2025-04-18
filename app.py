import os
import uuid
import io
import requests
from flask import Flask, render_template, request, send_from_directory, url_for
from PyPDF2 import PdfMerger
from werkzeug.utils import secure_filename
from PIL import Image, ImageFilter
from rembg import remove
# from rembg import remove, new_session  # 고급 설정 시 확장 가능
# import openai  # 이미지 생성 제거 시 주석처리
# from deep_translator import GoogleTranslator
# import replicate

app = Flask(__name__)

# 폴더 생성
app.config['UPLOAD_FOLDER'] = 'merged_pdfs'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/generated_images', exist_ok=True)
os.makedirs('static/resized_images', exist_ok=True)
os.makedirs('static/removed_bg', exist_ok=True)

# PDF 병합
@app.route('/pdf', methods=['GET','POST'])
def pdf():
    if request.method == 'POST':
        files = request.files.getlist('pdfs')
        filename = request.form.get('filename','').strip()
        if not files or len(files) < 2:
            return render_template('pdf_merge.html', error='PDF는 최소 2개 선택해주세요.')
        if not filename:
            return render_template('pdf_merge.html', error='파일명을 입력해주세요.')
        merger = PdfMerger()
        for f in files:
            if f.filename.lower().endswith('.pdf'):
                merger.append(f)
        safe_name = secure_filename(filename) + '.pdf'
        out_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
        merger.write(out_path)
        merger.close()
        return render_template('pdf_merge.html', merged_file_url=f'/download/{safe_name}')
    return render_template('pdf_merge.html')

# PDF 다운로드
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# 이미지 리사이즈
@app.route('/image-resize', methods=['GET','POST'])
def image_resize():
    resized_url = None
    upscaled_url = None
    if request.method == 'POST':
        img = request.files.get('image')
        w = request.form.get('width')
        h = request.form.get('height')
        compress = request.form.get('compress') == 'yes'
        outpaint = request.form.get('outpaint') == 'yes'
        if img:
            fname = f"orig_{uuid.uuid4()}.png"
            orig_path = os.path.join('static/resized_images', fname)
            img.save(orig_path)
            if outpaint:
                try:
                    im = Image.open(orig_path)
                    im = im.convert('RGB')
                    im.thumbnail((int(w), int(h)), Image.LANCZOS)
                    bg = Image.new('RGB', (int(w), int(h)), im.getpixel((0, 0)))
                    x = (int(w) - im.width) // 2
                    y = (int(h) - im.height) // 2
                    bg.paste(im, (x, y))
                    ext = 'webp' if compress else 'png'
                    out_name = f"resized_{uuid.uuid4()}.{ext}"
                    out_path = os.path.join('static/resized_images', out_name)
                    bg.save(out_path, format='WEBP' if compress else 'PNG')
                    resized_url = url_for('static', filename=f'resized_images/{out_name}')
                except Exception as e:
                    print('배경 확장 오류:', e)
                    resized_url = None
            elif w and h:
                w, h = int(w), int(h)
                im = Image.open(orig_path)
                im = im.convert('RGB')
                im = im.resize((w, h), Image.LANCZOS)
                ext = 'webp' if compress else 'png'
                out_name = f"resized_{uuid.uuid4()}.{ext}"
                out_path = os.path.join('static/resized_images', out_name)
                im.save(out_path, format='WEBP' if compress else 'PNG')
                resized_url = url_for('static', filename=f'resized_images/{out_name}')
    return render_template('image_resize.html', resized_url=resized_url, upscaled_url=upscaled_url)


@app.route('/remove-bg', methods=['GET', 'POST'])
def remove_bg():
    removed_url = None
    if request.method == 'POST':
        image = request.files.get('image')
        white_bg_option = request.form.get('white_bg') == 'yes'
        high_quality_option = request.form.get('high_quality') == 'yes'

        if image:
            input_data = image.read()
            try:
                if high_quality_option:
                    # 고급 모드: 1차 remove → 필터 → 2차 remove
                    original = Image.open(io.BytesIO(input_data)).convert("RGBA")
                    step1 = remove(original)
                    step1_image = Image.open(io.BytesIO(step1)).convert("RGBA")
                    step2 = step1_image.filter(ImageFilter.EDGE_ENHANCE)
                    buffered = io.BytesIO()
                    step2.save(buffered, format="PNG")
                    step2_bytes = buffered.getvalue()
                    step3 = remove(step2_bytes)
                    result_image = Image.open(io.BytesIO(step3)).convert("RGBA")
                else:
                    # 기본 모드
                    result = remove(input_data)
                    result_image = Image.open(io.BytesIO(result)).convert("RGBA")

                if white_bg_option:
                    white_bg = Image.new("RGBA", result_image.size, (255, 255, 255, 255))
                    result_image = Image.alpha_composite(white_bg, result_image)

                filename = f"removed_{uuid.uuid4()}.png"
                save_path = os.path.join("static/removed_bg", filename)
                result_image.save(save_path)
                removed_url = url_for('static', filename=f'removed_bg/{filename}')
            except Exception as e:
                print("고급모드 처리 중 오류 발생:", e)

    return render_template('remove_bg.html', removed_url=removed_url)


@app.route('/convert-format', methods=['GET', 'POST'])
def convert_format():
    converted_url = None
    if request.method == 'POST':
        image = request.files.get('image')
        format = request.form.get('format')
        if image and format:
            im = Image.open(image).convert("RGB")
            filename = f"converted_{uuid.uuid4()}.{format}"
            path = os.path.join("static/resized_images", filename)
            im.save(path, format=format.upper())
            converted_url = url_for('static', filename=f'resized_images/{filename}')
    return render_template('convert_format.html', converted_url=converted_url)


# 홈
@app.route('/')
def index():
    return render_template('index.html')

# 애플리케이션 실행
if __name__ == '__main__':
    app.run()
