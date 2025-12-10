import React, { useState } from 'react';
import { Link } from 'react-router-dom';

const API_BASE_URL = 'http://localhost:8000'; 

function FindPasswordPage() {
    // userId -> LoginId, name -> UserName으로 수정
    const [LoginId, setLoginId] = useState(''); 
    const [UserName, setUserName] = useState(''); 
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false); 

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        // 변수명 수정
        if (LoginId === '' || UserName === '') {
            setError('아이디와 이름을 모두 입력해주세요.');
            return;
        }

        setLoading(true);

        try {
            console.log('비밀번호 찾기 시도:', { LoginId, UserName });
            
            // TODO: 실제 서버로 비밀번호 찾기 요청 (임시 비밀번호 발급/이메일 전송)
            const response = await fetch(`${API_BASE_URL}/v1/auth/forgot-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    LoginId: LoginId,  // Pydantic 스키마 대소문자 일치
                    UserName: UserName // Pydantic 스키마 대소문자 일치
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '일치하는 정보가 없거나 오류가 발생했습니다.');
            }

            setSuccess('✅ 임시 비밀번호가 이메일로 전송되었습니다.');
            setError(''); 

        } catch (err) {
            console.error('비밀번호 찾기 에러:', err);
            setError(err.message || '알 수 없는 오류가 발생했습니다.');
            setSuccess('');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page-wrapper">
            <header className="auth-header-simple">
                <h1 className="page-title">
                    <Link to="/">HBI (How Big It Is?)</Link>
                </h1>
            </header>
            <main className="auth-main-container">
                <section className="auth-card-content">
                    <h3 className="auth-card-title">비밀번호 찾기</h3>

                    <form id="findPwForm" className="form-container" onSubmit={handleSubmit}>
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
                            <button 
                                id="findPwSubmit" 
                                type="submit" 
                                className="modal-save-btn" 
                                style={{ width: '100%' }}
                                disabled={loading}
                            >
                                {loading ? (
                                    <><i className="fas fa-spinner fa-spin mr-2"></i>처리 중...</>
                                ) : (
                                    '비밀번호 찾기'
                                )}
                            </button>
                        </div>
                    </form>

                    <footer className="auth-links-footer">
                        <Link to="/login">로그인</Link>
                        <span>|</span>
                        <Link to="/signup">회원가입</Link>
                    </footer>
                </section>
            </main>
        </div>
    );
}

export default FindPasswordPage;