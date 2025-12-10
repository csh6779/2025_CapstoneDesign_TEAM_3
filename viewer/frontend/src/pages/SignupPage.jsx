import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:9000';

function SignupPage() {
    const [LoginId, setLoginId] = useState('');
    const [UserName, setUserName] = useState('');
    const [Password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        // 비밀번호 확인 체크
        if (Password !== confirmPassword) {
            setError('비밀번호가 일치하지 않습니다.');
            return;
        }

        // 빈 값 체크
        if (LoginId === '' || UserName === '' || Password === '') {
            setError('모든 필드를 입력해주세요.');
            return;
        }

        setLoading(true);

        // ✅ formData 객체 생성
        const formData = {
            LoginId: LoginId,
            UserName: UserName,
            Password: Password
        };

        console.log('회원가입 요청 전송:', formData);
        console.log('API URL:', API_BASE_URL);

        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/auth/signup`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData), // ✅ 이제 formData 사용 가능
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '회원가입 실패');
            }

            const data = await response.json();
            console.log('회원가입 성공:', data);
            alert('회원가입이 완료되었습니다!');

            // 로그인 페이지로 리다이렉트
            navigate('/login');
        } catch (err) {
            console.error('회원가입 에러:', err);
            setError(err.message || '회원가입 중 오류가 발생했습니다.');
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
                    <h3 className="auth-card-title">회원가입</h3>

                    <form id="signupForm" className="form-container" onSubmit={handleSubmit}>
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
                                required
                                disabled={loading}
                            />
                        </div>

                        <div style={{ marginTop: '1rem' }}>
                            <label htmlFor="UserName" className="form-label">이름</label>
                            <input
                                type="text"
                                id="UserName"
                                name="UserName"
                                className="input-field"
                                placeholder="Name"
                                value={UserName}
                                onChange={(e) => setUserName(e.target.value)}
                                required
                                disabled={loading}
                            />
                        </div>

                        <div style={{ marginTop: '1rem' }}>
                            <label htmlFor="Password" className="form-label">비밀번호</label>
                            <input
                                type="password"
                                id="Password"
                                name="Password"
                                className="input-field"
                                placeholder="Password"
                                value={Password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                disabled={loading}
                            />
                        </div>

                        <div style={{ marginTop: '1rem' }}>
                            <label htmlFor="confirmPassword" className="form-label">비밀번호 확인</label>
                            <input
                                type="password"
                                id="confirmPassword"
                                name="confirmPassword"
                                className="input-field"
                                placeholder="Confirm Password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                required
                                disabled={loading}
                            />
                        </div>

                        {error && (
                            <p id="signupError" className="error-message">
                                {error}
                            </p>
                        )}

                        <div className="modal-action" style={{ marginTop: '1.5rem' }}>
                            <button 
                                id="signupSubmit" 
                                type="submit" 
                                className="modal-save-btn" 
                                style={{ width: '100%' }}
                                disabled={loading}
                            >
                                {loading ? (
                                    <><i className="fas fa-spinner fa-spin mr-2"></i>회원가입 처리 중...</>
                                ) : (
                                    '회원가입'
                                )}
                            </button>
                        </div>
                    </form>

                    <footer className="auth-links-footer">
                        <Link to="/login">로그인</Link>
                        <span>|</span>
                        <Link to="/find-password">비밀번호 찾기</Link>
                    </footer>
                </section>
            </main>
        </div>
    );
}

export default SignupPage;