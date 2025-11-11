import React, { useState } from 'react';
import { Link } from 'react-router-dom';

function FindPasswordPage() {
    // 폼 입력과 오류 메시지를 위한 State 생성
    const [userId, setUserId] = useState('');
    const [name, setName] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    // 폼 제출(submit) 시 실행될 함수 (auth.js의 findPwForm 로직)
    const handleSubmit = (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        if (userId === '' || name === '') {
            setError('아이디와 이름을 모두 입력해주세요.');
            return;
        }

        console.log('비밀번호 찾기 시도:', { userId, name });
        // TODO: 실제 서버로 비밀번호 찾기 요청 (userId, name 전송)
        
        // (시뮬레이션)
        // (실패 시) setError('일치하는 정보가 없습니다.');
        // (성공 시) setSuccess('임시 비밀번호가 이메일로 전송되었습니다.');
        
        setError('비밀번호 찾기 기능은 현재 준비 중입니다.');
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
                    <h3 className="auth-card-title">비밀번호 찾기</h3>

                    <form id="findPwForm" className="form-container" onSubmit={handleSubmit}>
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

                        {error && (
                            <p id="findPwResult" className="error-message">
                                {error}
                            </p>
                        )}
                        {success && (
                            <p id="findPwResult" className="error-message" style={{ color: 'green' }}>
                                {success}
                            </p>
                        )}

                        <div className="modal-action" style={{ marginTop: '1.5rem' }}>
                            <button id="findPwSubmit" type="submit" className="modal-save-btn" style={{ width: '100%' }}>비밀번호 찾기</button>
                        </div>
                    </form>

                    <footer className="auth-links-footer">
                        <Link to="/login">로그인</Link>
                        <span>|</span>
                        <Link to="/signup">회원가입</Link>
                        <span>|</span>
                        <Link to="/find-id">아이디 찾기</Link>
                    </footer>
                </section>
            </main>
        </div>
    );
}

export default FindPasswordPage;