from flask import Blueprint, jsonify, request
from ..utils.db import db
from ..utils.email_sender import generate_verification_code, send_verification_email
from datetime import datetime, timedelta
from bson import ObjectId
import os
import numpy as np
import uuid
from pymongo import MongoClient

attendance_routes = Blueprint('attendance', __name__)


@attendance_routes.route('/active-courses/<ogrno>', methods=['GET'])
def get_active_courses(ogrno):
    try:
        ogrno = str(ogrno)  # Bu satır eklendi
        print(f"[DEBUG] Öğrenci no: {ogrno} için aktif dersler getiriliyor")
        
        active_courses = list(db.attendance.find({
            "durum": "aktif",
            "tumOgrenciler": ogrno
        }))
        
        formatted_courses = []
        for course in active_courses:
            course_id = str(course['_id'])

            ogretmen = db.users.find_one({"mail": course.get('ogretmenMail')})
            ogretmen_adi = f"{ogretmen['ad']} {ogretmen['soyad']}" if ogretmen else course.get('ogretmenMail')

            katilim_yapildi = ogrno in course.get('katilanlar', [])

            formatted_courses.append({
                '_id': course_id,
                'dersKodu': course['dersKodu'],
                'dersAdi': course['dersAdi'],
                'katilimYapildi': katilim_yapildi,
                'ogretmenler': [ogretmen_adi],
                'tarih': course.get('tarih')
            })

        return jsonify(formatted_courses)

    except Exception as e:
        print(f"[HATA] Aktif dersler getirme hatası: {str(e)}")
        return jsonify({'error': str(e)}), 500

@attendance_routes.route('/verify-attendance/<ders_id>/<ogrno>', methods=['POST'])
def verify_attendance(ders_id, ogrno):
    try:
        # Dersi bul ve öğrenciyi katilanlar listesine ekle
        result = db.attendance.update_one(
            {"_id": ObjectId(ders_id)},
            {"$addToSet": {"katilanlar": ogrno}}
        )
        
        if result.modified_count > 0:
            print(f"[DEBUG] Öğrenci {ogrno} dersin katılımcılarına eklendi")
            return jsonify({"message": "Yoklama kaydı başarılı"}), 200
        else:
            print(f"[DEBUG] Öğrenci zaten katılımcılarda var veya güncelleme başarısız")
            return jsonify({"message": "Bu ders için zaten yoklama kaydınız var"}), 200
            
    except Exception as e:
        print(f"[HATA] Yoklama kaydı hatası: {str(e)}")
        return jsonify({'error': str(e)}), 500 

@attendance_routes.route('/student-tracking/<ogrno>', methods=['GET'])
def get_student_tracking(ogrno):
    try:
        # Öğrencinin tüm derslerini bul
        all_courses = list(db.attendance.find({
            "tumOgrenciler": ogrno
        }).distinct("dersKodu"))
        
        tracking_data = []
        
        for ders_kodu in all_courses:
            # Her ders için yoklama verilerini topla
            dersler = list(db.attendance.find({
                "dersKodu": ders_kodu,
                "tumOgrenciler": ogrno
            }))
            
            if dersler:
                toplam_ders = len(dersler)
                katildigi_ders = sum(1 for ders in dersler if ogrno in ders.get('katilanlar', []))
                katilmadigi_ders = toplam_ders - katildigi_ders
                katilim_orani = round((katildigi_ders / toplam_ders) * 100) if toplam_ders > 0 else 0
                
                tracking_data.append({
                    "dersKodu": ders_kodu,
                    "dersAdi": dersler[0].get('dersAdi', ''),
                    "toplamDers": toplam_ders,
                    "katildigiDers": katildigi_ders,
                    "katilmadigiDers": katilmadigi_ders,
                    "katilimOrani": katilim_orani
                })
        
        return jsonify(tracking_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 

@attendance_routes.route('/teacher-tracking/<teacher_mail>/<course_code>', methods=['GET'])
def get_teacher_tracking(teacher_mail, course_code):
    try:
        print(f"[DEBUG] Öğretmen devamsızlık takibi isteği - Öğretmen: {teacher_mail}, Ders: {course_code}")
        
        # Önce dersi bul
        course = db.courses.find_one({
            "dersKodu": course_code,
            "ogretmenler": teacher_mail
        })
        print(f"[DEBUG] Ders bulundu mu: {course is not None}")
        
        if not course:
            print("[DEBUG] Ders bulunamadı")
            return jsonify([])
            
        # Dersin tüm yoklama kayıtlarını bul
        all_attendance = list(db.attendance.find({
            "dersKodu": course_code,
            "ogretmenMail": teacher_mail
        }))
        print(f"[DEBUG] Bulunan yoklama kayıtları: {len(all_attendance)}")
        
        if not all_attendance:
            print("[DEBUG] Yoklama kaydı bulunamadı")
            return jsonify([])
            
        tracking_data = []
        
        # Her öğrenci için devamsızlık verilerini hesapla
        for ogrenci_no in course['ogrenciler']:
            print(f"[DEBUG] Öğrenci işleniyor: {ogrenci_no}")
            
            # Öğrenci bilgilerini al
            ogrenci = db.users.find_one({"ogrno": ogrenci_no})
            if not ogrenci:
                print(f"[DEBUG] Öğrenci bulunamadı: {ogrenci_no}")
                continue
                
            # Öğrencinin katıldığı dersleri say
            toplam_ders = len(all_attendance)
            katildigi_ders = sum(1 for ders in all_attendance if ogrenci_no in ders.get('katilanlar', []))
            katilmadigi_ders = toplam_ders - katildigi_ders
            katilim_orani = round((katildigi_ders / toplam_ders) * 100) if toplam_ders > 0 else 0
            
            print(f"[DEBUG] Öğrenci {ogrenci_no} - Toplam: {toplam_ders}, Katıldı: {katildigi_ders}, Katılmadı: {katilmadigi_ders}, Oran: {katilim_orani}")
            
            tracking_data.append({
                "ogrenciNo": ogrenci_no,
                "adSoyad": f"{ogrenci['ad']} {ogrenci['soyad']}",
                "toplamDers": toplam_ders,
                "katildigiDers": katildigi_ders,
                "katilmadigiDers": katilmadigi_ders,
                "katilimOrani": katilim_orani
            })
        
        print(f"[DEBUG] Toplam {len(tracking_data)} öğrenci verisi döndürülüyor")
        return jsonify(tracking_data)
        
    except Exception as e:
        print(f"[HATA] Öğretmen devamsızlık takibi hatası: {str(e)}")
        return jsonify({'error': str(e)}), 500 

@attendance_routes.route('/send-verification-email', methods=['POST'])
def send_verification_email_route():
    try:
        data = request.get_json()
        if not data or 'email' not in data:
            return jsonify({'error': 'E-posta adresi gerekli'}), 400
            
        # Doğrulama kodu oluştur
        verification_code = generate_verification_code()
        
        # Kodu veritabanına kaydet (5 dakika geçerli)
        db.verification_codes.insert_one({
            'email': data['email'],
            'code': verification_code,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(minutes=5)
        })
        
        # E-postayı gönder
        if send_verification_email(data['email'], verification_code):
            return jsonify({'message': 'Doğrulama kodu gönderildi'})
        else:
            return jsonify({'error': 'E-posta gönderilemedi'}), 500
            
    except Exception as e:
        print(f"E-posta gönderme hatası: {e}")
        return jsonify({'error': str(e)}), 500

@attendance_routes.route('/verify-email-code', methods=['POST'])
def verify_email_code():
    try:
        data = request.get_json()
        if not data or 'email' not in data or 'code' not in data:
            return jsonify({'error': 'E-posta ve kod gerekli'}), 400
            
        # Kodu kontrol et
        verification = db.verification_codes.find_one({
            'email': data['email'],
            'code': data['code'],
            'expires_at': {'$gt': datetime.now()}
        })
        
        if verification:
            # Kullanılmış kodu sil
            db.verification_codes.delete_one({'_id': verification['_id']})
            return jsonify({'message': 'Kod doğrulandı'})
        else:
            return jsonify({'error': 'Geçersiz veya süresi dolmuş kod'}), 400
            
    except Exception as e:
        print(f"Kod doğrulama hatası: {e}")
        return jsonify({'error': str(e)}), 500 

# Yüz tanıma için route
@attendance_routes.route('/face-upload/<student_id>', methods=['POST'])
def face_upload(student_id):
    try:
        print(f"[DEBUG] Face upload API çağrıldı. Student ID: {student_id}")
        print(f"[DEBUG] Request içeriği: {request.files}")
        print(f"[DEBUG] Form verileri: {request.form}")
        
        # Öğrenci ID kontrolü
        if not student_id:
            print("[ERROR] Öğrenci ID bilgisi eksik")
            return jsonify({'error': 'Öğrenci ID bilgisi eksik'}), 400
            
        # Öğrenci numarası form verilerinden geliyorsa kullan
        student_number = request.form.get('ogrno')
        student_ad = request.form.get('ad')
        student_soyad = request.form.get('soyad')
        
        if not student_number:
            print("[DEBUG] Form verilerinde öğrenci numarası yok, ID kullanılacak")
            student_number = student_id
            
        print(f"[DEBUG] Kullanılacak öğrenci numarası: {student_number}")
        
        image_file = request.files.get('file')
        
        if not image_file:
            print("[ERROR] Dosya gönderilmedi")
            return jsonify({'error': 'Dosya gönderilmedi'}), 400
            
        print(f"[DEBUG] Gelen dosya: {image_file.filename}, boyut: {image_file.content_length if hasattr(image_file, 'content_length') else 'bilinmiyor'}")
            
        # Klasörü oluştur - öğrenci numarası varsa onu kullan, yoksa ID'yi kullan
        folder_id = student_number
        save_path = os.path.join(os.getcwd(), 'face_data', folder_id)
        os.makedirs(save_path, exist_ok=True)
        print(f"[DEBUG] Klasör oluşturuldu: {save_path}")
        
        # Dosya adını garanti altına al
        filename = f"{uuid.uuid4()}.jpg"
        file_path = os.path.join(save_path, filename)
        
        # Dosyayı kaydet
        print(f"[DEBUG] Dosya kaydediliyor: {file_path}")
        image_file.save(file_path)
        print(f"[DEBUG] Dosya kaydedildi, boyut: {os.path.getsize(file_path)} bytes")
        
        try:
            print("[DEBUG] Face recognition işlemleri başlatılıyor")
            import face_recognition
            # Yüz tanıma işlemi
            print("[DEBUG] Görsel yükleniyor")
            image = face_recognition.load_image_file(file_path)
            print(f"[DEBUG] Görsel yüklendi, boyut: {image.shape}")
            
            print("[DEBUG] Yüz tespiti yapılıyor")
            face_locations = face_recognition.face_locations(image)
            
            print(f"[DEBUG] Tespit edilen yüz sayısı: {len(face_locations) if face_locations else 0}")
            
            if not face_locations:
                # Dosyayı sil (yüz tespit edilemedi)
                os.remove(file_path)
                print("[ERROR] Görselde yüz tespit edilemedi")
                return jsonify({'error': 'Görselde yüz tespit edilemedi'}), 400
                
            print("[DEBUG] Yüz özellikleri çıkarılıyor")
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if not face_encodings:
                # Dosyayı sil (encoding yapılamadı)
                os.remove(file_path)
                print("[ERROR] Yüz özellikleri çıkarılamadı")
                return jsonify({'error': 'Yüz özellikleri çıkarılamadı'}), 400
                
            print(f"[DEBUG] Yüz encoding'i oluşturuldu, boyut: {len(face_encodings[0])}")
            
            # Veritabanı bağlantısı varsa güncelle
            if db is not None:
                try:
                    print(f"[DEBUG] Ogrenciler koleksiyonu güncellemesi başlatılıyor. Öğrenci No: {student_number}")
                    
                    ogrenci_data = {
                        "ogrenci_id": student_number,
                        "ad": student_ad or "",
                        "soyad": student_soyad or "",
                        "encoding": face_encodings[0].tolist(),
                        "foto_galerisi": [file_path]
                    }
                    
                    # Öğrenci varsa güncelle, yoksa ekle (upsert)
                    result = db.ogrenciler.update_one(
                        {"ogrenci_id": student_number},
                        {"$set": ogrenci_data},
                        upsert=True
                    )
                    
                    print(f"[DEBUG] Ogrenciler güncelleme sonucu: matched_count={result.matched_count}, modified_count={result.modified_count}, upserted_id={result.upserted_id}")
                except Exception as db_err:
                    print(f"[ERROR] Ogrenciler güncelleme hatası: {str(db_err)}")
                    # Hata olsa bile işleme devam et
            else:
                print("[DEBUG] Veritabanı bağlantısı yok, sadece dosya kaydedildi")
            
            # Başarılı yanıt döndür (veritabanı güncellemesi yapılmasa bile)
            return jsonify({
                'message': 'Yüz verisi başarıyla kaydedildi',
                'face_path': file_path,
                'face_detected': True
            }), 200
            
        except ImportError as e:
            print(f"[ERROR] ImportError: {str(e)}")
            return jsonify({'error': 'Face recognition kütüphanesi yüklü değil'}), 500
            
    except Exception as e:
        print(f"[ERROR] Yüz verisi yükleme hatası: {str(e)}")
        import traceback
        print("[ERROR] Detaylı hata:")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# Yüz tanıma ile doğrulama için route
@attendance_routes.route('/face-verify', methods=['POST'])
def face_verify():
    try:
        print("[DEBUG] Face verify API çağrıldı")
        
        if 'file' not in request.files:
            print("[ERROR] Dosya gönderilmedi")
            return jsonify({'success': False, 'message': 'Dosya gönderilmedi'}), 400
            
        image_file = request.files['file']
        print(f"[DEBUG] Gelen dosya: {image_file.filename}")
        
        # Kurs ID'sini al
        course_id = request.form.get('courseId')
        if not course_id:
            print("[ERROR] Ders bilgisi eksik")
            return jsonify({'success': False, 'message': 'Ders bilgisi eksik'}), 400
        
        print(f"[DEBUG] CourseId: {course_id}")
        
        # MongoDB bağlantısı kontrolü
        if db is None:
            print("[ERROR] MongoDB bağlantısı yok, yüz tanıma yapılamayacak")
            return jsonify({'success': False, 'message': 'Veritabanı bağlantısı yok'}), 500
            
        try:
            import face_recognition
            
            # Gelen resimden yüz tanıma
            print("[DEBUG] Resim yükleniyor")
            image = face_recognition.load_image_file(image_file)
            
            print("[DEBUG] Yüz tespiti yapılıyor")
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                print("[ERROR] Görselde yüz tespit edilemedi")
                return jsonify({'success': False, 'message': 'Görselde yüz tespit edilemedi'}), 200
            
            print(f"[DEBUG] {len(face_locations)} adet yüz tespit edildi")
            
            print("[DEBUG] Yüz özellikleri çıkarılıyor")
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if not face_encodings:
                print("[ERROR] Yüz özellikleri çıkarılamadı")
                return jsonify({'success': False, 'message': 'Yüz özellikleri çıkarılamadı'}), 200
                
            input_encoding = face_encodings[0]
            
            # Sadece ogrenciler koleksiyonundan kontrol et
            print("[DEBUG] Ogrenciler koleksiyonundan öğrenciler alınıyor")
            try:
                ogrenciler = list(db.ogrenciler.find({"encoding": {"$exists": True}}))
                print(f"[DEBUG] {len(ogrenciler)} öğrenci bulundu (ogrenciler koleksiyonu)")
            except Exception as e:
                print(f"[ERROR] Veritabanı sorgusu hatası: {str(e)}")
                return jsonify({'success': False, 'message': 'Veritabanı sorgusu başarısız'}), 500
            
            best_match = None
            best_distance = 1.0  # Başlangıç değeri (0-1 arası, düşük daha iyi)
            
            for student in ogrenciler:
                if "encoding" not in student or not student["encoding"]:
                    continue
                    
                student_encoding = np.array(student["encoding"])
                
                if len(student_encoding) != 128:  # Face recognition 128 boyutlu vektör üretir
                    continue
                    
                # Yüz karşılaştırması yap
                face_distances = face_recognition.face_distance([student_encoding], input_encoding)
                
                if len(face_distances) > 0:
                    current_distance = face_distances[0]
                    print(f"[DEBUG] Öğrenci: {student.get('ad', '')} {student.get('soyad', '')}, Mesafe: {current_distance}")
                    
                    if current_distance < best_distance:
                        best_distance = current_distance
                        best_match = student
            
            # Eşleşme puanı 0.6'dan küçükse (daha iyi) kabul et
            if best_match and best_distance < 0.6:
                print(f"[DEBUG] Eşleşme bulundu: {best_match.get('ad', '')} {best_match.get('soyad', '')}, Mesafe: {best_distance}")
                
                student_id = best_match.get("ogrenci_id")
                if not student_id:
                    print("[ERROR] Eşleşen öğrencinin ogrenci_id değeri yok")
                    return jsonify({'success': False, 'message': 'Öğrenci kimliği bulunamadı'}), 200
                
                return jsonify({
                    'success': True, 
                    'ogrenci_id': student_id,
                    'ogrno': student_id,  # ogrenci_id ve ogrno aynı değer
                    'ad': best_match.get("ad", ""),
                    'soyad': best_match.get("soyad", "")
                }), 200
            else:
                print(f"[DEBUG] Eşleşme bulunamadı. En iyi mesafe: {best_distance}")
                return jsonify({'success': False, 'message': 'Eşleşen öğrenci bulunamadı'}), 200
                
        except ImportError as e:
            print(f"[ERROR] ImportError: {str(e)}")
            return jsonify({'success': False, 'message': 'Yüz tanıma kütüphanesi yüklenemedi'}), 500
            
    except Exception as e:
        print(f"[ERROR] Yüz tanıma hatası: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Bir hata oluştu: {str(e)}'}), 500 