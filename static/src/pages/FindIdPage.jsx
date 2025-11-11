import React, { useState } from 'react';
import { Link } from 'react-router-dom';

function FindIdPage() {
    // 2. 폼 입력과 오류 메시지를 위한 State 생성
    const [name, setName] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(''); // 성공 메시지 State

    // 3. 폼 제출(submit) 시 실행될 함수 (auth.js의 findIdForm 로직)
    const handleSubmit = (e) => {
        e.preventDefault(); // 폼 제출 중단
        setError('');   // 오류/성공 메시지 초기화
        setSuccess('');

        if (name === '' || password === '') {
            setError('이름과 비밀번호를 모두 입력해주세요.');
            return;
        }

        console.log('아이디 찾기 시도:', { name });
        // TODO: 실제 서버로 아이디 찾기 요청 (name, password 전송)
        
        // (시뮬레이션)
        // (실패 시) setError('일치하는 정보가 없습니다.');
        // (성공 시) setSuccess('회원님의 아이디는 [찾은 ID] 입니다.');
        
        // 현재는 준비 중 메시지만 표시
        setError('아이디 찾기 기능은 현재 준비 중입니다.');
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
                    <h3 className="auth-card-title">아이디 찾기</h3>

                    {/* 6. <form>에 onSubmit 핸들러 연결 */}
                    <form id="findIdForm" className="form-container" onSubmit={handleSubmit}>
                        <div>
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

                        {/* 10. 오류/성공 메시지 조건부 렌더링 */}
                        {error && (
                            <p id="findIdResult" className="error-message">
                                {error}
                            </p>
                        )}
                        {success && (
                            <p id="findIdResult" className="error-message" style={{ color: 'green' }}>
                                {success}
                            </p>
                        )}


                        <div className="modal-action" style={{ marginTop: '1.5rem' }}>
                            <button id="findIdSubmit" type="submit" className="modal-save-btn" style={{ width: '100%' }}>아이디 찾기</button>
                        </div>
                    </form>

                    <footer className="auth-links-footer">
                        <Link to="/login">로그인</Link>
                        <span>|</span>
                        <Link to="/signup">회원가입</Link>
                        <span>|</span>
                        <Link to="/find-password">비밀번호 찾기</Link>
                    </footer>
                </section>
            </main>
        </div>
    );
}

export default FindIdPage;