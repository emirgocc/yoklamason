import React, { useState, useCallback } from 'react';
import CameraCapture from './common/CameraCapture';

const FaceVerification = ({ courseId, onSuccess, onError, onCancel }) => {
  const [status, setStatus] = useState('waiting');
  const [message, setMessage] = useState('Kameraya erişim için hazırlanıyor...');
  const [error, setError] = useState(null);
  const [faceBlob, setFaceBlob] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showCamera, setShowCamera] = useState(false);

  const handleFaceCapture = (blob) => {
    setFaceBlob(blob);
    setShowCamera(false);
    setMessage('Fotoğraf çekildi. Yüz tanıma için gönderilmeye hazır.');
    setError(null);
  };

  const handleSubmit = useCallback(async () => {
    if (!faceBlob) {
      setError('Lütfen önce fotoğraf çekin.');
      return;
    }
    
    setIsProcessing(true);
    setStatus('processing');
    setMessage('Yüz tanıma işlemi başlatılıyor...');
    
    try {
      const formData = new FormData();
      formData.append('file', faceBlob, 'face.jpg');
      formData.append('courseId', courseId);
      
      console.log('[DEBUG] Yüz tanıma isteği gönderiliyor:', {
        courseId,
        blobSize: faceBlob.size
      });
      
      const response = await fetch('http://localhost:5000/api/attendance/face-verify', {
        method: 'POST',
        body: formData
      });
      
      console.log('[DEBUG] Yüz tanıma yanıtı alındı, status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('[ERROR] API yanıtı başarısız:', response.status, errorText);
        throw new Error(`API yanıtı başarısız: ${response.status} ${errorText}`);
      }
      
      let data;
      try {
        data = await response.json();
        console.log('[DEBUG] Yanıt verisi:', data);
      } catch (jsonError) {
        console.error('[ERROR] JSON ayrıştırma hatası:', jsonError);
        throw new Error('Sunucu yanıtı geçersiz JSON formatında');
      }
      
      if (data.success) {
        setStatus('success');
        setMessage('Yüz tanıma başarılı! Yoklamaya katılım onaylandı.');
        if (onSuccess) onSuccess(data);
      } else {
        setStatus('error');
        setMessage(data.message || 'Yüz tanıma başarısız!');
        setError(data.message || 'Yüz tanıma başarısız!');
        if (onError) onError(new Error(data.message || 'Yüz tanıma başarısız!'));
      }
    } catch (err) {
      console.error('[ERROR] Yüz tanıma işlemi hatası:', err);
      setStatus('error');
      setMessage('Hata: ' + (err.message || 'Bilinmeyen bir hata oluştu'));
      setError(err.message || 'Bilinmeyen bir hata oluştu');
      if (onError) onError(err);
    } finally {
      setIsProcessing(false);
    }
  }, [faceBlob, courseId, onSuccess, onError]);

  return (
    <div className="face-verification">
      <div className="notification is-light mb-4 has-text-centered">
        <div className="mb-3">
          {status === 'waiting' && (
            <span className="icon is-large">
              <i className="fas fa-spinner fa-pulse fa-2x"></i>
            </span>
          )}
          {status === 'processing' && (
            <span className="icon is-large">
              <i className="fas fa-camera fa-2x"></i>
            </span>
          )}
          {status === 'success' && (
            <span className="icon is-large has-text-success">
              <i className="fas fa-check-circle fa-2x"></i>
            </span>
          )}
          {status === 'error' && (
            <span className="icon is-large has-text-danger">
              <i className="fas fa-exclamation-triangle fa-2x"></i>
            </span>
          )}
        </div>
        <p className="is-size-5 mb-2">{message}</p>
        {error && <p className="has-text-danger is-size-7 mb-3">{error}</p>}
        {status !== 'success' && (
          <>
            {!faceBlob && !showCamera && (
              <button className="button is-info" onClick={() => setShowCamera(true)}>
                <span className="icon"><i className="fas fa-camera"></i></span>
                <span>Kamerayı Aç</span>
              </button>
            )}
            {showCamera && <CameraCapture onCapture={handleFaceCapture} onClose={() => setShowCamera(false)} />}
            {faceBlob && (
              <div className="mb-3">
                <img src={URL.createObjectURL(faceBlob)} alt="Çekilen yüz" style={{ maxWidth: 200, borderRadius: 8, border: '1px solid #ccc' }} />
                <button type="button" className="button is-warning is-small ml-2" onClick={() => setFaceBlob(null)}>
                  <span className="icon"><i className="fas fa-redo"></i></span>
                  <span>Yeniden Çek</span>
                </button>
              </div>
            )}
            <div className="mt-3">
              <button className="button is-primary" onClick={handleSubmit} disabled={!faceBlob || isProcessing}>
                {isProcessing ? 'Yüz Tanıma...' : 'Yüz Tanıma ile Doğrula'}
              </button>
              <button className="button is-light ml-2" onClick={onCancel}>
                İptal
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default FaceVerification; 