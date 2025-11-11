import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const API_BASE_URL = 'http://localhost:8000';

function LoginPage() {
    const [loginId, setLoginId] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (loginId === '' || password === '') {
            setError('아이디와 비밀번호를 모두 입력해주세요.');
            return;
        }

        setLoading(true);

        try {
            // FastAPI는 OAuth2 형식의 form data를 사용합니다
            const formData = new URLSearchParams();
            formData.append('username', loginId);
            formData.append('password', password);

            const response = await fetch(`${API_BASE_URL}/v1/auth/token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '로그인 실패');
            }

            const data = await response.json();

            // 토큰 및 사용자 정보 저장
            localStorage.setItem('accessToken', data.AccessToken);
            localStorage.setItem('userId', loginId);
            localStorage.setItem('userName', data.UserName || loginId);
            localStorage.setItem('userRank', 'Bronze'); // 기본 랭크

            console.log('로그인 성공:', {
                token: data.AccessToken,
                userId: loginId,
                userName: data.UserName
            });

            // 메인 페이지로 이동
            navigate('/');

        } catch (err) {
            console.error('로그인 에러:', err);
            setError(err.message || '아이디 또는 비밀번호가 일치하지 않습니다.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page-wrapper">
            <header className="auth-header-simple">
                <h1 className="page-title">
                    <Link to="/">대용량 이미지 뷰어</Link>
                </h1>
            </header>
            <main className="auth-main-container">
                <section className="auth-card-content">
                    <h3 className="auth-card-title">로그인</h3>

                    <form id="loginForm" className="form-container" onSubmit={handleSubmit}>
                        <div>
                            <label htmlFor="loginId" className="form-label">아이디</label>
                            <input
                                type="text"
                                id="loginId"
                                name="loginId"
                                className="input-field"
                                placeholder="ID"
                                value={loginId}
                                onChange={(e) => setLoginId(e.target.value)}
                                disabled={loading}
                            />
                        </div>

                        <div className="form-container">
                            <label htmlFor="password" className="form-label">비밀번호</label>
                            <input
                                type="password"
                                id="password"
                                name="password"
                                className="input-field"
                                placeholder="Password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                disabled={loading}
                            />
                        </div>

                        <div className="auth-checkbox-container">
                            <label className="auth-checkbox">
                                <input id="rememberMe" type="checkbox" />
                                로그인 유지
                            </label>
                        </div>

                        {error && (
                            <p id="loginError" className="error-message">
                                {error}
                            </p>
                        )}

                        <div className="modal-action" style={{ marginTop: '1.5rem' }}>
                            <button 
                                id="loginSubmit" 
                                type="submit" 
                                className="modal-save-btn" 
                                style={{ width: '100%' }}
                                disabled={loading}
                            >
                                {loading ? (
                                    <>
                                        <i className="fas fa-spinner fa-spin mr-2"></i>
                                        로그인 중...
                                    </>
                                ) : (
                                    '로그인'
                                )}
                            </button>
                        </div>
                    </form>

                    <footer className="auth-links-footer">
                        <Link to="/signup">회원가입</Link>
                        <span>|</span>
                        <Link to="/find-id">아이디 찾기</Link>
                        <span>|</span>
                        <Link to="/find-password">비밀번호 찾기</Link>
                    </footer>
                </section>
            </main>
        </div>
    );
}

export default LoginPage;
