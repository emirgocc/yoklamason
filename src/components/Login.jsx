import React, { useState, useEffect } from "react";

const Login = ({ onLogin }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    const savedUser = JSON.parse(localStorage.getItem("rememberMe"));
    if (savedUser && savedUser.username) {
      setUsername(savedUser.username);
    }
  }, []);

  const handleLogin = async () => {
    try {
      const loginData = {
        mail: username,
        sifre: password
      };

      console.log("Login isteği gönderiliyor:", loginData); // Debug log

      const response = await fetch('http://localhost:5000/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(loginData)
      });

      const data = await response.json();
      console.log("Login yanıtı:", data); // Debug log

      if (response.ok) {
        // Beni Hatırla seçeneği işaretliyse kullanıcı adını kaydet
        if (rememberMe) {
          localStorage.setItem("rememberMe", JSON.stringify({ username }));
        } else {
          localStorage.removeItem("rememberMe");
        }

        // Kullanıcı bilgilerini ve rolü ilet
        const userData = {
          mail: data.user.mail,
          role: data.user.role,
          ad: data.user.ad,
          soyad: data.user.soyad,
          ogrno: data.user.ogrno,
          username: `${data.user.ad} ${data.user.soyad}`
        };
        console.log("Login başarılı, userData:", userData); // Debug log
        onLogin(userData);
      } else {
        setError(data.error || 'Giriş başarısız');
      }
    } catch (error) {
      console.error('Login error:', error);
      setError('Bağlantı hatası: ' + error.message);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault(); // Formun varsayılan davranışını engelle
    handleLogin();
  };

  return (
    <>
     {error && (
        <div className="message-container">
          <div className="message is-danger">
            <div className="message-body">
              <button 
                className="delete" 
                aria-label="delete"
                onClick={() => setError("")}
              ></button>
              {error}
            </div>
          </div>
        </div>
      )}
      <p className="subtitle has-text-centered is-6 mb-4">
        Hoşgeldiniz, yoklama sistemine giriş yapınız.
      </p>

      {/* Form */}
      <form onSubmit={handleSubmit}>
        <div className="field">
          <div className="control">
            <input
              className="input"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Kurumsal e-postanızı girin"
            />
          </div>
        </div>

        <div className="field">
          <div className="control has-icons-right">
            <input
              className="input"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Şifrenizi girin"
            />
            <span 
              className="icon is-small is-right" 
              style={{ cursor: 'pointer', pointerEvents: 'all' }}
              onClick={() => setShowPassword(!showPassword)}
            >
              <i className={`fas ${showPassword ? 'fa-eye-slash' : 'fa-eye'}`}></i>
            </span>
          </div>
        </div>

        <div className="field">
          <label className="checkbox">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
            />{" "}
            Beni Hatırla
          </label>
        </div>

        <div className="field">
          <button
            type="submit"
            className="button is-primary is-fullwidth"
          >
            Giriş Yap
          </button>
        </div>
      </form>

    </>
  );
};

export default Login;