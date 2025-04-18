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


@app.route('/remove-bg', methods=['GET', 'POST'])
def remove_bg():
    removed_url = None
    if request.method == 'POST':
        image = request.files.get('image')
        white_bg_option = request.form.get('white_bg') == 'yes'
        high_quality_option = request.form.get('high_quality') == 'yes'

        if image:
            input_data = image.read()
            if high_quality_option:
                # 고급 모드: 1차 remove → 필터 → 2차 remove
                original = Image.open(io.BytesIO(input_data)).convert("RGBA")
                step1 = remove(original)
                step1_image = Image.open(io.BytesIO(step1)).convert("RGBA")
                step2 = step1_image.filter(ImageFilter.EDGE_ENHANCE)
                step3 = remove(step2)
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

    return render_template('remove_bg.html', removed_url=removed_url)
