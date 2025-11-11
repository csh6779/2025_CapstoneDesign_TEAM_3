import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

function SignupPage() {
    // 2. 폼 입력을 위한 'State' 5개(userId, name, password, confirmPassword, error)를 만듭니다.
    const [userId, setUserId] = useState('');
    const [name, setName] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState(''); // 오류 메시지 상태

    // 3. 페이지 이동을 위한 'useNavigate' 훅을 준비합니다.
    const navigate = useNavigate();

    // 4. 폼 제출(submit) 시 실행될 함수 (auth.js의 signupForm.addEventListener)
    const handleSubmit = (e) => {
        e.preventDefault(); // 실제 폼 제출 중단
        setError(''); // 이전 오류 메시지 초기화

        // 5. 유효성 검사 (auth.js 로직과 동일)
        if (userId === '' || name === '' || password === '' || confirmPassword === '') {
            setError('모든 필드를 입력해주세요.');
            return;
        }

        if (password !== confirmPassword) {
            setError('비밀번호가 일치하지 않습니다.');
            return;
        }

        console.log('회원가입 시도:', { userId, name });
        // TODO: 실제 서버로 회원가입 요청 (userId, name, password 값을 전송)

        // (시뮬레이션) 성공 알림 후 로그인 페이지로 이동
        alert('회원가입 성공! (시뮬레이션)\n로그인 페이지로 이동합니다.');
        navigate('/login'); // React 방식으로 페이지 이동
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

                    {/* 8. <form>에 onSubmit 이벤트 핸들러 연결 */}
                    <form id="signupForm" className="form-container" onSubmit={handleSubmit}>
                        <div>
                            <label htmlFor="userId" className="form-label">아이디</label>
                            <input
                                type="text"
                                id="userId"
                                name="userId"
                                className="input-field"
                                placeholder="ID"
                                value={userId}
                                onChange={(e) => setUserId(e.target.value)}
                                required
                            />
                        </div>

                        <div style={{ marginTop: '1rem' }}>
                            <label htmlFor="name" className="form-label">이름</label>
                            <input
                                type="text"
                                id="name"
                                name="name"
                                className="input-field"
                                placeholder="Name"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                required
                            />
                        </div>

                        <div style={{ marginTop: '1rem' }}>
                            <label htmlFor="password" className="form-label">비밀번호</label>
                            <input
                                type="password"
                                id="password"
                                name="password"
                                className="input-field"
                                placeholder="Password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
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
                            />
                        </div>

                        {/* 12. <p> 태그 대신 'State'를 사용한 조건부 렌더링 */}
                        {error && (
                            <p id="signupError" className="error-message">
                                {error}
                            </p>
                        )}

                        <div className="modal-action" style={{ marginTop: '1.5rem' }}>
                            <button id="signupSubmit" type="submit" className="modal-save-btn" style={{ width: '100%' }}>회원가입</button>
                        </div>
                    </form>

                    <footer className="auth-links-footer">
                        <Link to="/login">로그인</Link>
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

export default SignupPage;