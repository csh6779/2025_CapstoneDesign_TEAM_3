import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:9000';

function LoginPage() {
    const [LoginId, setLoginId] = useState('');
    const [Password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (LoginId === '' || Password === '') {
            setError('아이디와 비밀번호를 모두 입력해주세요.');
            return;
        }

        setLoading(true);

        try {
            // Step 1: 로그인으로 토큰 받기
            const formData = new URLSearchParams();
            formData.append('username', LoginId);
            formData.append('password', Password);

            const tokenResponse = await fetch(`${API_BASE_URL}/api/v1/auth/token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData
            });

            if (!tokenResponse.ok) {
                const errorData = await tokenResponse.json();
                throw new Error(errorData.detail || '로그인 실패');
            }

            const tokenData = await tokenResponse.json();
            const accessToken = tokenData.AccessToken || tokenData.access_token;

            // Step 2: 토큰으로 사용자 정보 가져오기
            const userResponse = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                },
            });

            if (!userResponse.ok) {
                throw new Error('사용자 정보를 가져올 수 없습니다.');
            }

            const userData = await userResponse.json();

            // 로컬 스토리지 저장
            localStorage.setItem('accessToken', accessToken);
            localStorage.setItem('LoginId', userData.LoginId);
            localStorage.setItem('UserName', userData.UserName);
            localStorage.setItem('Role', userData.Role.toLowerCase());
            localStorage.setItem('userRank', 'Bronze');

            console.log('로그인 성공:', {
                token: accessToken,
                user: userData,
            });

            // 역할에 따라 페이지 이동
            if (userData.Role.toLowerCase() === 'admin') {
                navigate('/admin');
            } else {
                navigate('/');
            }

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
                            <label htmlFor="LoginId" className="form-label">아이디</label>
                            <input
                                type="text"
                                id="LoginId"
                                name="LoginId"
                                className="input-field"
                                placeholder="ID"
                                value={LoginId}
                                onChange={(e) => setLoginId(e.target.value)}
                                disabled={loading}
                            />
                        </div>

                        <div className="form-container">
                            <label htmlFor="Password" className="form-label">비밀번호</label>
                            <input
                                type="password"
                                id="Password"
                                name="Password"
                                className="input-field"
                                placeholder="Password"
                                value={Password}
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
                        <Link to="/find-password">비밀번호 찾기</Link>
                    </footer>
                </section>
            </main>
        </div>
    );
}

export default LoginPage;