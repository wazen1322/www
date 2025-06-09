from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os
import csv
import socket
from datetime import datetime

app = Flask(__name__)

# ملف إعدادات الحماية
ملف_الحماية = "ip_settings.json"
ملف_البيانات = "الاشتراكات.json"
ملف_السجل = "access_log.json"

# تحميل إعدادات الحماية
def تحميل_إعدادات_الحماية():
    try:
        with open(ملف_الحماية, "r", encoding="utf-8") as ملف:
            return json.load(ملف)
    except FileNotFoundError:
        return {"الحماية_مفعلة": False, "الآي_بيز_المسموحة": []}

# حفظ إعدادات الحماية
def حفظ_إعدادات_الحماية(الإعدادات):
    with open(ملف_الحماية, "w", encoding="utf-8") as ملف:
        json.dump(الإعدادات, ملف, ensure_ascii=False, indent=4)

# الحصول على IP الحالي
def الحصول_على_الآي_بي():
    return request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', '127.0.0.1'))

# فحص الحماية
def فحص_الحماية():
    الإعدادات = تحميل_إعدادات_الحماية()
    الآي_بي_الحالي = الحصول_على_الآي_بي()
    
    if الإعدادات["الحماية_مفعلة"]:
        if الآي_بي_الحالي not in الإعدادات["الآي_بيز_المسموحة"]:
            حفظ_سجل_الوصول(الآي_بي_الحالي, "محاولة وصول مرفوضة", "فشل")
            return False
        else:
            حفظ_سجل_الوصول(الآي_بي_الحالي, "وصول مسموح", "نجح")
    else:
        حفظ_سجل_الوصول(الآي_بي_الحالي, "وصول بدون حماية", "نجح")
    
    return True

# تحميل البيانات من الملف
def تحميل_البيانات():
    try:
        with open(ملف_البيانات, "r", encoding="utf-8") as ملف:
            return json.load(ملف)
    except FileNotFoundError:
        return []

# حفظ البيانات إلى الملف
def حفظ_البيانات(الاشتراكات):
    with open(ملف_البيانات, "w", encoding="utf-8") as ملف:
        json.dump(الاشتراكات, ملف, ensure_ascii=False, indent=4)

# حساب الأيام المتبقية
def حساب_الأيام_المتبقية(تاريخ_الانتهاء):
    اليوم = datetime.today().date()
    نهاية = datetime.strptime(تاريخ_الانتهاء, '%Y-%m-%d').date()
    return (نهاية - اليوم).days

# حفظ سجل الوصول
def حفظ_سجل_الوصول(الآي_بي, العملية, الحالة):
    try:
        with open(ملف_السجل, "r", encoding="utf-8") as ملف:
            السجلات = json.load(ملف)
    except FileNotFoundError:
        السجلات = []
    
    سجل_جديد = {
        "التاريخ_والوقت": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "الآي_بي": الآي_بي,
        "العملية": العملية,
        "الحالة": الحالة
    }
    
    السجلات.append(سجل_جديد)
    
    # الاحتفاظ بآخر 1000 سجل فقط
    if len(السجلات) > 1000:
        السجلات = السجلات[-1000:]
    
    with open(ملف_السجل, "w", encoding="utf-8") as ملف:
        json.dump(السجلات, ملف, ensure_ascii=False, indent=4)

@app.route('/')
def الصفحة_الرئيسية():
    if not فحص_الحماية():
        return render_template('access_denied.html', ip=الحصول_على_الآي_بي())

    الاشتراكات = تحميل_البيانات()
    # تحديث الأيام المتبقية
    for اشتراك in الاشتراكات:
        اشتراك["الأيام المتبقية"] = حساب_الأيام_المتبقية(اشتراك["تاريخ الانتهاء"])
    حفظ_البيانات(الاشتراكات)

    return render_template('index.html', subscriptions=الاشتراكات)

@app.route('/add_subscription', methods=['POST'])
def إضافة_اشتراك():
    if not فحص_الحماية():
        return jsonify({'error': 'Access denied'}), 403

    الاشتراكات = تحميل_البيانات()

    اشتراك_جديد = {
        "اسم العميل": request.form['customer_name'],
        "بريد الحساب": request.form['email'],
        "كلمة المرور": request.form['password'],
        "رقم الملف": request.form['file_number'],
        "نوع الاشتراك": request.form['subscription_type'],
        "تاريخ البداية": request.form['start_date'],
        "تاريخ الانتهاء": request.form['end_date'],
        "الأيام المتبقية": حساب_الأيام_المتبقية(request.form['end_date'])
    }

    الاشتراكات.append(اشتراك_جديد)
    حفظ_البيانات(الاشتراكات)

    return redirect(url_for('الصفحة_الرئيسية'))

@app.route('/delete_subscription/<int:index>')
def حذف_اشتراك(index):
    if not فحص_الحماية():
        return jsonify({'error': 'Access denied'}), 403

    الاشتراكات = تحميل_البيانات()
    if 0 <= index < len(الاشتراكات):
        الاشتراكات.pop(index)
        حفظ_البيانات(الاشتراكات)

    return redirect(url_for('الصفحة_الرئيسية'))

@app.route('/delete_all')
def حذف_جميع_الاشتراكات():
    if not فحص_الحماية():
        return jsonify({'error': 'Access denied'}), 403

    حفظ_البيانات([])
    return redirect(url_for('الصفحة_الرئيسية'))

@app.route('/ip_management')
def إدارة_الآي_بيز():
    الإعدادات = تحميل_إعدادات_الحماية()
    الآي_بي_الحالي = الحصول_على_الآي_بي()
    return render_template('ip_management.html', 
                         settings=الإعدادات, 
                         current_ip=الآي_بي_الحالي)

@app.route('/update_ip_settings', methods=['POST'])
def تحديث_إعدادات_الآي_بي():
    الإعدادات = تحميل_إعدادات_الحماية()

    action = request.form.get('action')

    if action == 'toggle_protection':
        الإعدادات["الحماية_مفعلة"] = request.form.get('protection_enabled') == 'on'

    elif action == 'add_ip':
        ip = request.form.get('ip_address')
        if ip and ip not in الإعدادات["الآي_بيز_المسموحة"]:
            # التحقق من صحة الـ IP
            try:
                parts = ip.split('.')
                if len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts):
                    الإعدادات["الآي_بيز_المسموحة"].append(ip)
            except:
                pass

    elif action == 'add_current':
        current_ip = الحصول_على_الآي_بي()
        if current_ip not in الإعدادات["الآي_بيز_المسموحة"]:
            الإعدادات["الآي_بيز_المسموحة"].append(current_ip)

    elif action == 'delete_ip':
        ip_to_delete = request.form.get('ip_to_delete')
        if ip_to_delete in الإعدادات["الآي_بيز_المسموحة"]:
            الإعدادات["الآي_بيز_المسموحة"].remove(ip_to_delete)

    حفظ_إعدادات_الحماية(الإعدادات)
    return redirect(url_for('إدارة_الآي_بيز'))

@app.route('/export_csv')
def تصدير_CSV():
    if not فحص_الحماية():
        return jsonify({'error': 'Access denied'}), 403

    الاشتراكات = تحميل_البيانات()

    # إنشاء ملف CSV في الذاكرة
    import io
    output = io.StringIO()
    writer = csv.writer(output)

    # كتابة العناوين
    writer.writerow(["اسم العميل", "بريد الحساب", "كلمة المرور", "رقم الملف", 
                     "نوع الاشتراك", "تاريخ البداية", "تاريخ الانتهاء", "الأيام المتبقية"])

    # كتابة البيانات
    for اشتراك in الاشتراكات:
        writer.writerow([اشتراك["اسم العميل"], اشتراك["بريد الحساب"], 
                        اشتراك["كلمة المرور"], اشتراك["رقم الملف"],
                        اشتراك["نوع الاشتراك"], اشتراك["تاريخ البداية"], 
                        اشتراك["تاريخ الانتهاء"], اشتراك["الأيام المتبقية"]])

    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=subscriptions.csv"}
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
import shutil
import os

# الدالة التي تنشئ ملف ZIP
def إنشاء_ملف_مضغوط():
    # اسم الملف المضغوط
    اسم_الملف = "برنامج_الاشتراكات.zip"
    # مسار المجلد الذي يحتوي على الملفات
    مسار_المجلد = "."

    # إنشاء ملف مضغوط
    shutil.make_archive(اسم_الملف.replace('.zip', ''), 'zip', مسار_المجلد)

# استدعاء الدالة
if __name__ == '__main__':
    إنشاء_ملف_مضغوط()
    print("تم إنشاء الملف المضغوط بنجاح.")