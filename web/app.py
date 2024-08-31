from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
import json
import requests
import chardet
from werkzeug.utils import secure_filename
from werkzeug.exceptions import NotFound
import dashscope
from dashscope import MultiModalConversation
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///meter.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
MAX_BALANCE = 9999

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
# Set the working directory to the directory this file is in
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Load configuration file
with open('config/qwen.json', 'r') as config_file:
    config = json.load(config_file)

# Set DashScope API key
dashscope.api_key = config['api_key']
# 读取 WxPusher 配置
with open('config/wxpush.json', 'rb') as f:
    raw_data = f.read()
    detected = chardet.detect(raw_data)
    encoding = detected['encoding']
with open('config/wxpush.json', 'r', encoding=encoding) as f:
    wxpush_config = json.load(f)

db = SQLAlchemy(app)

class MeterData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    last_balance = db.Column(db.Float, default=100)
    last_recharge_reading = db.Column(db.Float, default=5000)
    warn_balance = db.Column(db.Float, default=300)

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)
    reading = db.Column(db.Float)

class MeterReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reading = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_manual_correction = db.Column(db.Boolean, default=False)

class OperationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    operation_type = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.String(50))
    details = db.Column(db.Text)

with app.app_context():
    db.create_all()

def log_operation(operation_type, user_id, details):
    log = OperationLog(operation_type=operation_type, user_id=user_id, details=details)
    db.session.add(log)
    db.session.commit()

def get_current_balance():
    meter_data = MeterData.query.first()
    if not meter_data:
        return MAX_BALANCE
    latest_reading = MeterReading.query.order_by(MeterReading.timestamp.desc()).first()
    if not latest_reading:
        return MAX_BALANCE
    return meter_data.last_recharge_reading + meter_data.last_balance - latest_reading.reading

def get_warn_balance():
    meter_data = MeterData.query.first()
    return meter_data.warn_balance

def send_wxpusher_alert():
    url = "https://wxpusher.zjiecode.com/api/send/message"
    headers = {"Content-Type": "application/json"}
    wxpush_config['content'] = wxpush_config['content'].replace('${ROOM}', '2502')
    wxpush_config['content'] = wxpush_config['content'].replace('${BALANCE}', str(get_current_balance()))
    response = requests.post(url, json=wxpush_config, headers=headers)
    if response.status_code == 200:
        result = response.json()
        if result['success']:
            logging.info('报警消息已成功发送')
            flash('报警消息已成功发送', 'success')
        else:
            logging.error(f'发送报警消息失败: {result["msg"]}')
            flash(f'发送报警消息失败: {result["msg"]}', 'error')
    else:
        logging.error(f"Failed to send alert via wxpush: HTTP {response.status_code}")
        flash(f'发送报警消息失败: HTTP {response.status_code}', 'error')

def check_balance_and_send_alert():
    current_balance = get_current_balance()
    if current_balance < get_warn_balance():
        send_wxpusher_alert()

def recognize_meter_reading(image_path):
    try:
        response = MultiModalConversation.call(
            model='qwen-vl-plus',
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {'image': image_path},
                        {'text': '请识别这张图片中的电表读数，电表读数是6位整数，只返回数字，不要有任何文字和符号。如果你不能识别度数，返回-1。'}
                    ]
                }
            ]
        )
        if response.status_code == 200:
            # Assuming the model returns a numeric string
            reading = float(response.output.choices[0].message.content[0]['text'].strip())
            if reading < 0:
                logging.warning("Failed to recognize meter reading")
                return None
            return reading
        else:
            logging.error(f"Error: {response.code}, {response.message}")
            return None
    except Exception as e:
        logging.error(f"Error recognizing meter reading: {str(e)}")
        return None

@app.before_request
def block_sensitive_dirs():
    if request.path.startswith(('/config/', '/instance/')):
        raise NotFound()
    logging.info(f"Request: {request.path}")

@app.route('/')
def index():
    # Get the latest meter reading
    latest_reading = MeterReading.query.order_by(MeterReading.timestamp.desc()).first()
    current_reading = latest_reading.reading if latest_reading else None

    # Get the current balance (assuming you have a Balance model)
    current_balance = get_current_balance()

    # Get the last uploaded image
    last_image = Image.query.order_by(Image.upload_time.desc()).first()
    last_image_path = os.path.join('static/uploads', last_image.filename) if last_image else None

    # Get the last log entry
    last_log = OperationLog.query.order_by(OperationLog.timestamp.desc()).first()

    return render_template('index.html',
                           current_reading=current_reading,
                           current_balance=current_balance,
                           last_image=last_image_path,
                           last_log=last_log)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        user_id = request.form.get('user_id', '0001')
        file = request.files.get('file')
        if file and file.filename:
            try:
                filename = secure_filename(file.filename)
                ts = datetime.now()
                now = ts.strftime("%Y%m%d_%H%M%S")
                filename = f"{user_id}_{now}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                # 识别电表读数
                meter_reading = recognize_meter_reading(file_path)
                if meter_reading is not None:
                    new_reading = MeterReading(reading=meter_reading, is_manual_correction=False, timestamp=ts)
                    db.session.add(new_reading)
                    db.session.commit()
                    flash(f'文件上传成功，识别的电表读数为: {meter_reading}', 'success')
                else:
                    flash('文件上传成功，但无法识别电表读数', 'warning')
                    return

                # 保存图片记录
                new_image = Image(filename=filename, upload_time=ts)
                db.session.add(new_image)
                db.session.commit()
                log_operation('file_upload', user_id, f'Uploaded file: {filename}, Reading: {meter_reading}, Timestamp: {ts}')

                # 只保留最近10张图片
                old_images = Image.query.order_by(Image.upload_time.desc()).offset(10).all()
                for old_image in old_images:
                    # 删除文件系统中的图片
                    old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], old_image.filename)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                    # 从数据库中删除记录
                    db.session.delete(old_image)
                db.session.commit()

                # 检查是否需要发送报警
                check_balance_and_send_alert()
            except Exception as e:
                logging.error(f"Error uploading file: {str(e)}")
                flash(f'文件上传失败: {str(e)}', 'error')
            return redirect(url_for('upload_file'))
        else:
            logging.warning("No file selected for upload")
            flash('没有选择文件', 'warning')

    # 获取最新的电表读数
    latest_reading = MeterReading.query.order_by(MeterReading.timestamp.desc()).first()
    current_reading = latest_reading.reading if latest_reading else None
    is_manual_correction = latest_reading.is_manual_correction if latest_reading else False

    # 获取最新上传的图片
    latest_image = Image.query.order_by(Image.upload_time.desc()).first()
    latest_image_filename = latest_image.filename if latest_image else None

    images = Image.query.order_by(Image.upload_time.desc()).limit(10).all()
    image_paths = [os.path.join('static/uploads', image.filename) for image in images]
    return render_template('upload.html',
                           images=image_paths,
                           current_reading=current_reading,
                           is_manual_correction=is_manual_correction,
                           latest_image=latest_image_filename)

@app.route('/manual_correction', methods=['POST'])
def manual_correction():
    if request.method == 'POST':
        manual_reading = request.form.get('manual_reading')
        latest_image = request.form.get('latest_image')

        # 检查最新的图片是否与传入的一致
        db_latest_image = Image.query.order_by(Image.upload_time.desc()).first()
        image_ts = db_latest_image.upload_time
        if db_latest_image and db_latest_image.filename == latest_image:
            if manual_reading:
                try:
                    reading = float(manual_reading)
                    # 获取最后一条 MeterReading 记录
                    last_reading = MeterReading.query.order_by(MeterReading.timestamp.desc()).first()

                    # 检查最后一条记录的图片是否与 latest_image 一致
                    if last_reading.timestamp == image_ts:
                        # 修改最后一条记录
                        last_reading.reading = reading
                        last_reading.is_manual_correction = True
                        db.session.commit()
                    else:
                        # 如果不一致，返回错误
                        flash('无法校正：最新图片已更新，请刷新页面后重试', 'error')
                        return redirect(url_for('upload_file'))
                    log_operation('manual_correction', 'admin', f'Manual correction: {reading}, Image: {latest_image}')
                    flash('电表读数已手动校正', 'success')
                    # 检查是否需要发送报警
                    check_balance_and_send_alert()
                except ValueError:
                    flash('无效的读数值', 'error')
            else:
                flash('请输入读数', 'warning')
        else:
            flash('无法校正：最新图片已更新，请刷新页面后重试', 'error')

    return redirect(url_for('upload_file'))

@app.route('/meter', methods=['GET', 'POST'])
def meter_management():
    meter_data = MeterData.query.first()
    if not meter_data:
        meter_data = MeterData()
        db.session.add(meter_data)
        db.session.commit()

    # 获取最新的电表读数
    latest_reading = MeterReading.query.order_by(MeterReading.timestamp.desc()).first()
    current_reading = latest_reading.reading if latest_reading else None
    is_manual_correction = latest_reading.is_manual_correction if latest_reading else False
    current_balance = get_current_balance()

    if request.method == 'POST':
        if 'reset' in request.form:
            old_last_balance = meter_data.last_balance
            old_last_recharge_reading = meter_data.last_recharge_reading
            old_warn_balance = meter_data.warn_balance

            new_last_balance = float(request.form.get('last_balance', meter_data.last_balance))
            meter_data.last_recharge_reading = float(request.form.get('last_recharge_reading', meter_data.last_recharge_reading))
            meter_data.warn_balance = float(request.form.get('warn_balance', meter_data.warn_balance))

            # 如果余额被手动修改，添加新的电表读数记录
            if new_last_balance != old_last_balance:
                new_reading = MeterReading(reading=new_last_balance, is_manual_correction=True)
                db.session.add(new_reading)
                meter_data.last_balance = new_last_balance
                current_reading = new_last_balance
                is_manual_correction = True

            db.session.commit()

            log_operation('meter_reset', 'admin', f'Last balance: {old_last_balance} -> {meter_data.last_balance}, '
                                                  f'Last recharge reading: {old_last_recharge_reading} -> {meter_data.last_recharge_reading}, '
                                                  f'Warn balance: {old_warn_balance} -> {meter_data.warn_balance}')

            flash('电表数据已更新', 'success')
        elif 'trigger_alarm' in request.form:
            send_wxpusher_alert()
            log_operation('alarm_triggered', 'admin', f'Current balance: {meter_data.last_balance}')
            logging.warning("Alarm triggered")
            flash('报警已触发！当前余额低于警戒值', 'warning')

    return render_template('meter.html', meter_data=meter_data, current_reading=current_reading, is_manual_correction=is_manual_correction, current_balance=current_balance)

@app.route('/logs')
def view_logs():
    logs = OperationLog.query.order_by(OperationLog.timestamp.desc()).limit(100).all()
    return render_template('logs.html', logs=logs)

@app.route('/clean_logs', methods=['POST'])
def clean_logs():
    try:
        num_deleted = OperationLog.query.delete()
        db.session.commit()
        flash(f'成功清除 {num_deleted} 条日志记录', 'success')

        # Log the cleaning operation
        log_operation('clean_logs', 'admin', f'Cleaned {num_deleted} log entries')
    except Exception as e:
        db.session.rollback()
        flash(f'清除日志失败: {str(e)}', 'error')
        logging.error(f'Log cleaning error: {str(e)}')

    return redirect(url_for('view_logs'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)