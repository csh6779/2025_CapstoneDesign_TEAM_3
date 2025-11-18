import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const API_BASE_URL = 'http://localhost:8000'; 

function SignupPage() {
    // loginId -> LoginId, userName -> UserName으로 수정
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

        // 변수명 수정
        if (LoginId === '' || UserName === '' || Password === '' || confirmPassword === '') { 
            setError('모든 필드를 입력해주세요.');
            return;
        }

        // Password 변수 사용
        if (Password !== confirmPassword) {
            setError('비밀번호가 일치하지 않습니다.');
            return;
        }

        setLoading(true);

        try {
            console.log('회원가입 요청 전송:', { LoginId, UserName, Password });

            // TODO: 실제 서버로 회원가입 요청 (DB 저장 로직)
            const response = await fetch(`${API_BASE_URL}/v1/users`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    LoginId: LoginId,  // Pydantic 스키마 일치 (변수와 키가 일치)
                    Password: Password,
                    UserName: UserName, // Pydantic 스키마 일치 (변수와 키가 일치)
                    Role: 'user'
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                if (response.status === 409) {
                    throw new Error('이미 존재하는 아이디입니다.');
                }
                throw new Error(errorData.detail || '회원가입 실패');
            }

            alert('회원가입 성공! 로그인 페이지로 이동합니다.');
            navigate('/login');

        } catch (err) {
            console.error('회원가입 에러:', err);
            setError(err.message || '알 수 없는 오류가 발생했습니다.');
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
                                onChange={(e) => setPassword(e.target.value)} // setPassword로 변경
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