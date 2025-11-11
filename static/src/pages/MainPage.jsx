import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';

// --- 전역 상수 ---
const PLACEHOLDER_IMAGE_URL = 'https://placehold.co/150x150/E2E8F0/4A5568?text=User';
const RANK_DETAILS = {
    'Bronze': { icon: 'fas fa-medal', class: 'bronze' },
    'Silver': { icon: 'fas fa-award', class: 'silver' },
    'Gold': { icon: 'fas fa-trophy', class: 'gold' }
};
const DEFAULT_RANK = 'Bronze';
const API_BASE_URL = 'http://localhost:8000';

function MainPage() {

    // --- State 정의 ---
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);
    const [isVerifySectionVisible, setIsVerifySectionVisible] = useState(true);
    const [toast, setToast] = useState({ message: '', visible: false });
    const [user, setUser] = useState({ userId: 'Guest', userName: '', rank: '', profileImg: PLACEHOLDER_IMAGE_URL });
    const [files, setFiles] = useState([]);
    const [profilePreview, setProfilePreview] = useState(PLACEHOLDER_IMAGE_URL);
    const [passwordForm, setPasswordForm] = useState({ verifyId: '', verifyCurrentPassword: '', newPassword: '', confirmPassword: '' });

    // 새로 추가된 State
    const [volumes, setVolumes] = useState([]);
    const [currentVolume, setCurrentVolume] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [expandedVolumes, setExpandedVolumes] = useState(new Set());

    const navigate = useNavigate();
    const fileInputRef = useRef(null);
    let toastTimer;


    // --- useEffect: 페이지 로드 시 실행 ---
    useEffect(() => {
    const storedUserId = localStorage.getItem('userId');
    
    if (storedUserId) {
    const storedUserName = localStorage.getItem('userName') || '사용자';
    let storedRank = localStorage.getItem('userRank');
    if (!storedRank) {
    storedRank = DEFAULT_RANK;
    localStorage.setItem('userRank', storedRank);
    }
    const storedProfileImg = localStorage.getItem('profileImage') || PLACEHOLDER_IMAGE_URL;

    setUser({
    userId: storedUserId,
    userName: storedUserName,
    rank: storedRank,
    profileImg: storedProfileImg
    });
    
    // 로그인된 경우 볼륨 목록 로드
    const loadInitialVolumes = async () => {
            try {
            const token = localStorage.getItem('accessToken');
                if (!token) return;

                const response = await fetch(`${API_BASE_URL}/api/volumes`, {
                headers: {
                        'Authorization': `Bearer ${token}`
                        }
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        setVolumes(data.volumes || []);
                    }
                } catch (error) {
                    console.error('볼륨 로드 실패:', error);
                }
            };
            
            loadInitialVolumes();
        } else {
            setUser({ userId: 'Guest', userName: '', rank: '', profileImg: PLACEHOLDER_IMAGE_URL });
        }

        return () => {
            if (toastTimer) clearTimeout(toastTimer);
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // --- 볼륨 관리 함수 ---
    const loadVolumes = async (username = user.userId) => {
        try {
            const token = localStorage.getItem('accessToken');
            if (!token) return;

            const response = await fetch(`${API_BASE_URL}/api/volumes?username=${username}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                setVolumes(data.volumes || []);
            }
        } catch (error) {
            console.error('볼륨 로드 실패:', error);
        }
    };

    const handleVolumeClick = (volume) => {
        setCurrentVolume(volume);
        showToast(`📊 ${volume.name} 뷰어에 로드됨`);
    };

    const handleDeleteVolume = async (volumeName, event) => {
        event.stopPropagation();

        if (!window.confirm(`"${volumeName}"을(를) 삭제하시겠습니까?`)) {
            return;
        }

        try {
            const token = localStorage.getItem('accessToken');
            const response = await fetch(
                `${API_BASE_URL}/api/volumes/${volumeName}?username=${user.userId}`,
                {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                }
            );

            if (response.ok) {
                showToast(`🗑️ ${volumeName} 삭제 완료`);

                // 현재 뷰어에 표시 중이었다면 초기화
                if (currentVolume?.name === volumeName) {
                    setCurrentVolume(null);
                }

                // 목록 새로고침
                await loadVolumes();
            } else {
                const error = await response.json();
                showToast(`❌ 삭제 실패: ${error.detail}`);
            }
        } catch (error) {
            showToast(`❌ 삭제 중 오류: ${error.message}`);
        }
    };

    const toggleVolumeExpand = (volumeName) => {
        const newExpanded = new Set(expandedVolumes);
        if (newExpanded.has(volumeName)) {
            newExpanded.delete(volumeName);
        } else {
            newExpanded.add(volumeName);
        }
        setExpandedVolumes(newExpanded);
    };

    // --- 이벤트 핸들러 ---
    const showToast = (message) => {
        if (toastTimer) clearTimeout(toastTimer);
        setToast({ message, visible: true });
        toastTimer = setTimeout(() => {
            setToast({ message: '', visible: false });
        }, 3000);
    };

    const handleOpenDrawer = () => setIsDrawerOpen(true);
    const handleCloseDrawer = () => setIsDrawerOpen(false);

    const handleOpenModal = () => {
        const storedUserId = localStorage.getItem('userId');
        if (!storedUserId) {
            navigate('/login');
            return;
        }

        const storedProfileImage = localStorage.getItem('profileImage') || PLACEHOLDER_IMAGE_URL;
        setProfilePreview(storedProfileImage);

        setIsVerifySectionVisible(true);
        setPasswordForm({ verifyId: storedUserId, verifyCurrentPassword: '', newPassword: '', confirmPassword: '' });

        setIsModalOpen(true);
    };

    const handleCloseModal = () => setIsModalOpen(false);

    const handleOpenLogHistory = () => {
        window.open('/log-history', '_blank');
    };

    const handleLogout = () => {
        handleCloseModal();
        setIsLogoutModalOpen(true);
    };

    const handleCloseLogoutModal = () => setIsLogoutModalOpen(false);

    const handleConfirmLogout = () => {
        localStorage.removeItem('userId');
        localStorage.removeItem('userName');
        localStorage.removeItem('profileImage');
        localStorage.removeItem('userRank');
        localStorage.removeItem('accessToken');

        handleCloseLogoutModal();

        setUser({ userId: 'Guest', userName: '', rank: '', profileImg: PLACEHOLDER_IMAGE_URL });
        setVolumes([]);
        setCurrentVolume(null);
        showToast("로그아웃되었습니다.");
    };

    // --- 파일 업로드 핸들러 ---
    const handleFileDrop = (e) => {
        e.preventDefault();
        e.currentTarget.classList.remove('active');
        setFiles(prevFiles => [...prevFiles, ...e.dataTransfer.files]);
        showToast(`📁 총 ${e.dataTransfer.files.length}개의 파일이 추가되었습니다.`);
    };

    const handleFileSelect = (e) => {
        setFiles(prevFiles => [...prevFiles, ...e.target.files]);
        showToast(`📁 총 ${e.target.files.length}개의 파일이 추가되었습니다.`);
    };

    const handleDeleteFile = (fileToRemove) => {
        setFiles(prevFiles => prevFiles.filter(file => file !== fileToRemove));
        showToast('🗑️ 파일이 목록에서 제거되었습니다.');
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.currentTarget.classList.add('active');
    };

    const handleDragLeave = (e) => e.currentTarget.classList.remove('active');

    // 청크 분해 (업로드 및 변환)
    const handleChunkConversion = async () => {
        if (files.length === 0) {
            showToast('⚠️ 업로드할 파일을 먼저 선택해주세요.');
            return;
        }

        const token = localStorage.getItem('accessToken');
        if (!token) {
            showToast('⚠️ 로그인이 필요합니다.');
            navigate('/login');
            return;
        }

        setUploading(true);
        setUploadProgress(0);

        try {
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                showToast(`📤 ${file.name} 업로드 중... (${i + 1}/${files.length})`);

                const formData = new FormData();
                formData.append('file', file);

                const response = await fetch(`${API_BASE_URL}/api/upload`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    },
                    body: formData
                });

                if (response.ok) {
                    const result = await response.json();
                    showToast(`✅ ${file.name} 청크 변환 완료!`);

                    // 첫 번째 파일을 자동으로 뷰어에 로드
                    if (i === 0) {
                        setCurrentVolume(result);
                    }
                } else {
                    const error = await response.json();
                    showToast(`❌ ${file.name} 실패: ${error.detail}`);
                }

                setUploadProgress(((i + 1) / files.length) * 100);
            }

            // 업로드 완료 후 볼륨 목록 새로고침
            await loadVolumes();
            setFiles([]);

        } catch (error) {
            showToast(`❌ 업로드 중 오류: ${error.message}`);
        } finally {
            setUploading(false);
            setUploadProgress(0);
        }
    };

    // 프로필 이미지 관리
    const handleImagePreview = (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => {
                setProfilePreview(reader.result);
            };
            reader.readAsDataURL(file);
        }
    };

    const handleDeleteImage = () => setProfilePreview(PLACEHOLDER_IMAGE_URL);

    const handleSubmitProfileImage = () => {
        let newImageSrc = profilePreview;

        if (newImageSrc === PLACEHOLDER_IMAGE_URL) {
            localStorage.setItem('profileImage', PLACEHOLDER_IMAGE_URL);
        } else if (newImageSrc.startsWith('data:image')) {
            localStorage.setItem('profileImage', newImageSrc);
        } else {
            newImageSrc = localStorage.getItem('profileImage') || PLACEHOLDER_IMAGE_URL;
        }

        setUser(prevUser => ({
            ...prevUser,
            profileImg: newImageSrc
        }));

        showToast('✅ 이미지가 저장되었습니다.');
        handleCloseModal();
    };

    // 비밀번호 변경
    const handlePasswordFormChange = (e) => {
        const { name, value } = e.target;
        setPasswordForm(prev => ({ ...prev, [name]: value }));
    };

    const handleVerifyUser = () => {
        if (passwordForm.verifyId === user.userId && passwordForm.verifyCurrentPassword === 'admin123') {
            showToast('✅ 본인 확인이 완료되었습니다.');
            setIsVerifySectionVisible(false);
        } else {
            showToast('❌ 아이디 또는 현재 비밀번호가 일치하지 않습니다.');
        }
    };

    const handleSubmitNewPassword = () => {
        if (passwordForm.newPassword.length < 6) {
            showToast("비밀번호는 최소 6자 이상이어야 합니다.");
            return;
        }
        if (passwordForm.newPassword !== passwordForm.confirmPassword) {
            showToast("비밀번호가 일치하지 않습니다.");
            return;
        }
        showToast('🔒 비밀번호가 성공적으로 변경되었습니다.');
        handleCloseModal();
    };

    // Neuroglancer URL 생성
    const getNeuroglancerUrl = (volume) => {
        if (!volume) return '';

        const config = {
            layers: [
                {
                    type: 'image',
                    source: volume.neuroglancer_url,
                    name: volume.name,
                    tab: 'rendering'
                }
            ],
            layout: '4panel',
            showAxisLines: false
        };

        return `https://neuroglancer-demo.appspot.com/#!${encodeURIComponent(JSON.stringify(config))}`;
    };

    return (
        <div className="body-page">
            {/* 드로어 오버레이 */}
            <div
                id="drawerOverlay"
                className={`drawer-overlay ${isDrawerOpen ? 'overlay-visible' : ''}`}
                onClick={handleCloseDrawer}
            ></div>

            {/* 드로어 */}
            <div id="uploadDrawer" className={`upload-drawer ${isDrawerOpen ? 'drawer-visible' : ''}`}>
                <div className="drawer-header">
                    <h3>사진 업로드</h3>
                    <button id="drawerCloseBtn" className="drawer-close-btn" onClick={handleCloseDrawer}>
                        <i className="fas fa-times"></i>
                    </button>
                </div>

                <div className="drawer-content">
                    {/* 파일 업로드 영역 */}
                    <div
                        id="dropzone"
                        className="dropzone"
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleFileDrop}
                    >
                        <i className="fas fa-cloud-upload-alt upload-box-icon"></i>
                        <p className="gray-font">파일을 드래그하세요</p>
                        <p className="muted">또는</p>
                        <input
                            type="file"
                            id="fileInput"
                            multiple
                            className="hidden"
                            ref={fileInputRef}
                            onChange={handleFileSelect}
                            accept=".png,.jpg,.jpeg,.tiff,.tif"
                        />
                        <button id="browseBtn" className="file-btn" onClick={() => fileInputRef.current.click()}>
                            파일 찾기
                        </button>
                    </div>

                    {/* 업로드된 파일 목록 */}
                    <div className="file-list">
                        <div className="flex items-center justify-between mb-3">
                            <h3 className="file-list-title">업로드된 파일</h3>
                            {files.length > 0 && (
                                <button
                                    onClick={handleChunkConversion}
                                    disabled={uploading}
                                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-sm font-medium transition"
                                >
                                    {uploading ? (
                                        <>
                                            <i className="fas fa-spinner fa-spin mr-2"></i>
                                            변환 중...
                                        </>
                                    ) : (
                                        <>
                                            <i className="fas fa-cut mr-2"></i>
                                            청크 분해
                                        </>
                                    )}
                                </button>
                            )}
                        </div>

                        <div id="fileList" className="file-list-body">
                            {files.map((file, index) => (
                                <div key={index} className="file-item">
                                    <div className="file-item-info">
                                        <div className="file-item-name">{file.name}</div>
                                        <div className="file-item-size">{(file.size / 1024).toFixed(1)} KB</div>
                                    </div>
                                    <button className="file-item-delete-btn" onClick={() => handleDeleteFile(file)}>
                                        <i className="fas fa-trash-alt"></i>
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* 변환된 볼륨 목록 */}
                    {volumes.length > 0 && (
                        <div className="volume-list mt-4">
                            <h3 className="file-list-title mb-3">
                                <i className="fas fa-folder-open mr-2"></i>
                                내 이미지 ({volumes.length})
                            </h3>
                            <div className="space-y-2">
                                {volumes.map((volume) => (
                                    <div key={volume.name} className="volume-item-container">
                                        <div
                                            className={`volume-item-header ${currentVolume?.name === volume.name ? 'active' : ''}`}
                                            onClick={() => toggleVolumeExpand(volume.name)}
                                        >
                                            <div className="flex items-center flex-1">
                                                <i className={`fas fa-chevron-${expandedVolumes.has(volume.name) ? 'down' : 'right'} mr-2 text-xs`}></i>
                                                <i className="fas fa-image mr-2"></i>
                                                <span className="font-medium text-sm">{volume.name}</span>
                                            </div>
                                            <div className="volume-actions">
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleVolumeClick(volume);
                                                    }}
                                                    className="volume-action-btn view"
                                                    title="뷰어에 표시"
                                                >
                                                    <i className="fas fa-eye"></i>
                                                </button>
                                                <button
                                                    onClick={(e) => handleDeleteVolume(volume.name, e)}
                                                    className="volume-action-btn delete"
                                                    title="삭제"
                                                >
                                                    <i className="fas fa-trash"></i>
                                                </button>
                                            </div>
                                        </div>

                                        {expandedVolumes.has(volume.name) && (
                                            <div className="volume-details">
                                                <div className="volume-detail-item">
                                                    <span className="volume-detail-label">크기:</span>
                                                    <span className="volume-detail-value">
                                                        {volume.dimensions?.join(' × ')}
                                                    </span>
                                                </div>
                                                <div className="volume-detail-item">
                                                    <span className="volume-detail-label">청크:</span>
                                                    <span className="volume-detail-value">
                                                        {volume.chunk_size?.join(' × ')}
                                                    </span>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* 메인 컨테이너 */}
            <div className="app-container">
                {/* 헤더 */}
                <header className="page-header">
                    <button id="hamburgerBtn" className="hamburger-btn" onClick={handleOpenDrawer}>
                        <i className="fas fa-bars"></i>
                    </button>
                    <h1 className="page-title">
                        <Link to="/">대용량 이미지 뷰어</Link>
                    </h1>
                    <div className="page-nav">
                        {user.userId === 'Guest' ? (
                            <Link to="/login" id="loginBtn" className="header-login-btn">
                                <i className="fas fa-sign-in-alt"></i>
                                <span>로그인</span>
                            </Link>
                        ) : (
                            <div id="userProfileGroup" className="page-nav-group">
                                <div id="headerUserRank" className={`header-user-rank ${RANK_DETAILS[user.rank]?.class || 'bronze'}`}>
                                    <i id="headerRankIcon" className={RANK_DETAILS[user.rank]?.icon || 'fas fa-medal'}></i>
                                    <span id="headerRankName">{user.rank}</span>
                                </div>
                                <span id="headerUserId" className="header-user-id">{user.userName || user.userId}</span>
                                <button className="profile-btn" onClick={handleOpenModal}>
                                    <img src={user.profileImg} alt="프로필" id="mainProfileImg" />
                                </button>
                            </div>
                        )}
                    </div>
                </header>

                {/* Neuroglancer 뷰어 */}
                <div className="main-content-area">
                    <div className="neuroglancer-panel">
                        <div className="neuroglancer-container" id="viewer3D">
                            {currentVolume ? (
                                <iframe
                                    key={currentVolume.name}
                                    title="Neuroglancer 뷰어"
                                    src={getNeuroglancerUrl(currentVolume)}
                                    className="neuroglancer-iframe"
                                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                />
                            ) : (
                                <div className="flex items-center justify-center h-full bg-gray-100">
                                    <div className="text-center text-gray-500">
                                        <i className="fas fa-image text-6xl mb-4 opacity-30"></i>
                                        <p className="text-lg font-medium">이미지를 업로드하고</p>
                                        <p className="text-sm">청크 분해를 실행하세요</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* 업로드 진행 모달 */}
            {uploading && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                        <div className="flex items-center mb-4">
                            <i className="fas fa-spinner fa-spin text-blue-600 text-2xl mr-3"></i>
                            <h3 className="text-lg font-semibold">청크 변환 중...</h3>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
                            <div
                                className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                                style={{ width: `${uploadProgress}%` }}
                            ></div>
                        </div>
                        <p className="text-sm text-gray-600 text-center">
                            {uploadProgress.toFixed(0)}% 완료
                        </p>
                        <p className="text-xs text-gray-500 text-center mt-2">
                            파일을 업로드하고 청크로 변환하는 중입니다...
                        </p>
                    </div>
                </div>
            )}

            {/* 계정 관리 모달 */}
            <div
                id="accountModal"
                className={`modal-backdrop modal-transition ${isModalOpen ? 'modal-visible' : 'modal-hidden'}`}
                onClick={(e) => { if (e.target === e.currentTarget) handleCloseModal(); }}
            >
                <div className="modal-content">
                    <nav className="modal-nav">
                        <h2 className="modal-title">계정 관리</h2>
                        <ul className="modal-nav-list">
                            <li>
                                <button id="tab-profile-btn" className="modal-nav-btn active">
                                    <i className="fas fa-user-edit w-5"></i> 내정보 수정
                                </button>
                            </li>
                            <li>
                                <button className="modal-nav-btn" onClick={handleOpenLogHistory}>
                                    <i className="fas fa-history w-5"></i> 로그 내역
                                </button>
                            </li>
                        </ul>
                        <div className="modal-nav-footer">
                            <button className="modal-nav-logout" onClick={handleLogout}>로그아웃</button>
                        </div>
                    </nav>

                    <div className="modal-body">
                        <div id="tab-profile">
                            <h3 className="modal-body-title">내정보 수정</h3>
                            <div className="profile-image-area">
                                <div
                                    className="profile-image-wrapper"
                                    onMouseOver={(e) => e.currentTarget.querySelector('.profile-image-delete-btn').style.opacity = '0.5'}
                                    onMouseOut={(e) => e.currentTarget.querySelector('.profile-image-delete-btn').style.opacity = '0'}
                                >
                                    <img src={profilePreview} alt="프로필 사진" id="profilePreview" className="profile-image-preview" />
                                    <button className="profile-image-delete-btn" id="deleteImageBtn" onClick={handleDeleteImage}>
                                        <i className="fas fa-times"></i>
                                    </button>
                                </div>
                                <label htmlFor="photoInput" className="profile-image-change-btn">
                                    이미지 변경 <input type="file" accept="image/*" id="photoInput" className="hidden" onChange={handleImagePreview} />
                                </label>
                            </div>

                            <div className="modal-action">
                                <button className="modal-save-btn" onClick={handleSubmitProfileImage}>이미지 저장</button>
                            </div>

                            <div className="form-section-spaced" style={{ borderTop: '1px solid #E5E7EB', marginTop: '2rem', paddingTop: '2rem' }}>
                                <h3 className="modal-body-title">비밀번호 변경</h3>

                                {isVerifySectionVisible ? (
                                    <div id="verifySection">
                                        <p className="form-note">보안을 위해 현재 사용자 정보를 확인합니다.</p>
                                        <div className="form-container">
                                            <div>
                                                <label htmlFor="verifyId" className="form-label">현재 사용자 ID</label>
                                                <input
                                                    type="text"
                                                    id="verifyId"
                                                    name="verifyId"
                                                    className="input-field"
                                                    value={passwordForm.verifyId}
                                                    onChange={handlePasswordFormChange}
                                                    readOnly
                                                />
                                            </div>
                                            <div>
                                                <label htmlFor="verifyCurrentPassword" className="form-label">현재 비밀번호</label>
                                                <input
                                                    type="password"
                                                    id="verifyCurrentPassword"
                                                    name="verifyCurrentPassword"
                                                    className="input-field"
                                                    placeholder="현재 비밀번호"
                                                    value={passwordForm.verifyCurrentPassword}
                                                    onChange={handlePasswordFormChange}
                                                />
                                            </div>
                                        </div>
                                        <div className="modal-action">
                                            <button className="modal-cancel-btn" onClick={handleCloseModal}>취소</button>
                                            <button className="modal-save-btn" onClick={handleVerifyUser}>본인 확인</button>
                                        </div>
                                    </div>
                                ) : (
                                    <div id="newPasswordSection" className="form-section-spaced">
                                        <div className="form-container">
                                            <div>
                                                <label htmlFor="newPassword" className="form-label">새 비밀번호</label>
                                                <input
                                                    type="password"
                                                    id="newPassword"
                                                    name="newPassword"
                                                    placeholder="6자 이상 입력해주세요"
                                                    className="input-field"
                                                    value={passwordForm.newPassword}
                                                    onChange={handlePasswordFormChange}
                                                />
                                            </div>
                                            <div>
                                                <label htmlFor="confirmPassword" className="form-label">비밀번호 확인</label>
                                                <input
                                                    type="password"
                                                    id="confirmPassword"
                                                    name="confirmPassword"
                                                    placeholder="다시 한번 입력해주세요"
                                                    className="input-field"
                                                    value={passwordForm.confirmPassword}
                                                    onChange={handlePasswordFormChange}
                                                />
                                            </div>
                                        </div>
                                        <div className="modal-action">
                                            <button className="modal-cancel-btn" onClick={handleCloseModal}>취소</button>
                                            <button className="modal-succes-btn" onClick={handleSubmitNewPassword}>비밀번호 변경</button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* 로그아웃 확인 모달 */}
            <div
                id="logoutConfirmModal"
                className={`modal-backdrop modal-transition ${isLogoutModalOpen ? 'modal-visible' : 'modal-hidden'}`}
                onClick={(e) => { if (e.target === e.currentTarget) handleCloseLogoutModal(); }}
            >
                <div className="modal-content-confirm">
                    <h3 className="modal-body-title">로그아웃</h3>
                    <p className="form-note">정말로 로그아웃 하시겠습니까?</p>
                    <div className="modal-actions-center">
                        <button className="modal-cancel-btn" onClick={handleCloseLogoutModal}>취소</button>
                        <button className="modal-logout-btn" onClick={handleConfirmLogout}>로그아웃</button>
                    </div>
                </div>
            </div>

            {/* 토스트 메시지 */}
            <div id="toast" className={`toast-popup ${toast.visible ? 'visible' : ''}`}>
                <p id="toast-message">{toast.message}</p>
            </div>
        </div>
    );
}

export default MainPage;
