// frontend/src/pages/AdminPage.jsx
// ✅ 로컬 Neuroglancer 서버 통합 버전

import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import '../AdminPage.css';

// --- 전역 상수 ---
const PLACEHOLDER_IMAGE_URL = 'https://placehold.co/150x150/E2E8F0/4A5568?text=Admin';
const RANK_DETAILS = {
    'Bronze': { icon: 'fas fa-medal', class: 'bronze' },
    'Silver': { icon: 'fas fa-award', class: 'silver' },
    'Gold': { icon: 'fas fa-trophy', class: 'gold' },
    'Admin': { icon: 'fas fa-user-shield', class: 'gold' }
};
const API_BASE_URL = 'http://localhost:9000';

function AdminPage() {

    // --- State 정의 ---
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);
    const [isVerifySectionVisible, setIsVerifySectionVisible] = useState(true);
    const [toast, setToast] = useState({ message: '', visible: false });

    const [adminUser, setAdminUser] = useState({
        LoginId: 'Admin',
        UserName: '관리자',
        rank: 'Admin',
        profileImg: PLACEHOLDER_IMAGE_URL
    });

    const [files, setFiles] = useState([]);
    const [profilePreview, setProfilePreview] = useState(PLACEHOLDER_IMAGE_URL);
    const [passwordForm, setPasswordForm] = useState({
        VerifyId: '',
        VerifyCurrentPassword: '',
        NewPassword: '',
        ConfirmPassword: ''
    });

    const [volumes, setVolumes] = useState([]);
    const [currentVolume, setCurrentVolume] = useState(null);
    const [neuroglancerUrl, setNeuroglancerUrl] = useState(''); // ✅ 로컬 API용 State
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [expandedVolumes, setExpandedVolumes] = useState(new Set());

    const [isUploadSectionOpen, setIsUploadSectionOpen] = useState(true);
    const [isMyImageSectionOpen, setIsMyImageSectionOpen] = useState(true);
    const [isBookmarkSectionOpen, setIsBookmarkSectionOpen] = useState(false);

    const navigate = useNavigate();
    const pageLocation = useLocation();
    const fileInputRef = useRef(null);
    let toastTimer;

    // --- 초기화 (Auth Check & Data Load) ---
    useEffect(() => {
        const token = localStorage.getItem('accessToken');
        const role = (localStorage.getItem('Role') || '').toLowerCase();

        if (!token || role !== 'admin') {
            alert('관리자 권한이 필요합니다.');
            navigate('/login');
            return;
        }

        const storedLoginId = localStorage.getItem('LoginId');
        const storedUserName = localStorage.getItem('UserName') || '관리자';
        const storedProfileImg = localStorage.getItem('profileImage') || PLACEHOLDER_IMAGE_URL;

        setAdminUser({
            LoginId: storedLoginId || 'Admin',
            UserName: storedUserName,
            rank: 'ADMIN', 
            profileImg: storedProfileImg
        });

        const loadInitial = async () => {
            if (pageLocation.state && pageLocation.state.selectedDatasets && pageLocation.state.selectedDatasets.length > 0) {
                const passedDatasets = pageLocation.state.selectedDatasets;
                setVolumes(passedDatasets);
                setCurrentVolume(passedDatasets[0]);
            } else {
                await loadVolumes();
            }
        };

        loadInitial();

        return () => {
            if (toastTimer) clearTimeout(toastTimer);
        };
    }, [navigate, pageLocation.state]);

    // ✅ currentVolume이 변경될 때 Neuroglancer URL 생성
    useEffect(() => {
        const loadNeuroglancerUrl = async () => {
            if (currentVolume) {
                const url = await getNeuroglancerUrl(currentVolume);
                setNeuroglancerUrl(url);
            } else {
                setNeuroglancerUrl('');
            }
        };
        
        loadNeuroglancerUrl();
    }, [currentVolume]);

    // --- 볼륨 관리 ---
    const loadVolumes = async () => {
        try {
            const token = localStorage.getItem('accessToken');
            if (!token) return;

            const response = await fetch(`${API_BASE_URL}/api/volumes`, {
                headers: { 'Authorization': `Bearer ${token}` }
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

        if (!window.confirm(`"${volumeName}"을(를) 삭제하시겠습니까?`)) return;

        try {
            const token = localStorage.getItem('accessToken');
            const response = await fetch(
                `${API_BASE_URL}/api/volumes/${encodeURIComponent(volumeName)}`,
                {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${token}` }
                }
            );

            if (response.ok) {
                showToast(`🗑️ ${volumeName} 삭제 완료`);
                if (currentVolume?.name === volumeName) setCurrentVolume(null);
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

    const toggleMyImageSection = () => setIsMyImageSectionOpen(!isMyImageSectionOpen);

    // --- UI 핸들러 ---
    const showToast = (message) => {
        if (toastTimer) clearTimeout(toastTimer);
        setToast({ message, visible: true });
        toastTimer = setTimeout(() => {
            setToast({ message: '', visible: false });
        }, 5000);
    };

    const handleToggleDrawer = () => setIsDrawerOpen(prev => !prev);
    const handleCloseDrawer = () => setIsDrawerOpen(false);

    const handleOpenModal = () => {
        const storedLoginId = localStorage.getItem('LoginId');
        if (!storedLoginId) {
            navigate('/login');
            return;
        }
        const storedProfileImage = localStorage.getItem('profileImage') || PLACEHOLDER_IMAGE_URL;
        setProfilePreview(storedProfileImage);
        setIsVerifySectionVisible(true);
        setPasswordForm({ VerifyId: storedLoginId, VerifyCurrentPassword: '', NewPassword: '', ConfirmPassword: '' });
        setIsModalOpen(true);
    };

    const handleCloseModal = () => setIsModalOpen(false);
    const handleOpenLogHistory = () => window.open('/log-history', '_blank');

    const handleLogout = () => {
        handleCloseModal();
        setIsLogoutModalOpen(true);
    };

    const handleCloseLogoutModal = () => setIsLogoutModalOpen(false);
    const handleConfirmLogout = () => {
        localStorage.clear();
        handleCloseLogoutModal();
        setAdminUser({ LoginId: 'Guest', UserName: '', rank: '', profileImg: PLACEHOLDER_IMAGE_URL });
        setVolumes([]);
        setCurrentVolume(null);
        showToast("로그아웃되었습니다.");
        navigate('/login');
    };

    // --- 파일 핸들러 ---
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
                formData.append('LoginId', adminUser.LoginId);

                const response = await fetch(`${API_BASE_URL}/api/upload`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` },
                    body: formData
                });

                if (response.ok) {
                    const result = await response.json();
                    showToast(`✅ ${file.name} 청크 변환 완료!`);
                    if (i === 0) setCurrentVolume(result);
                } else {
                    const error = await response.json();
                    showToast(`❌ ${file.name} 실패: ${error.detail}`);
                }
                setUploadProgress(((i + 1) / files.length) * 100);
            }
            await loadVolumes();
            setFiles([]);
        } catch (error) {
            showToast(`❌ 업로드 중 오류: ${error.message}`);
        } finally {
            setUploading(false);
            setUploadProgress(0);
        }
    };

    // --- 계정 관련 핸들러 ---
    const handleImagePreview = (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => setProfilePreview(reader.result);
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
        setAdminUser(prev => ({ ...prev, profileImg: newImageSrc }));
        showToast('✅ 이미지가 저장되었습니다.');
        handleCloseModal();
    };

    const handlePasswordFormChange = (e) => {
        const { name, value } = e.target;
        setPasswordForm(prev => ({ ...prev, [name]: value }));
    };

    const handleVerifyUser = () => {
        if (passwordForm.VerifyId === adminUser.LoginId && passwordForm.VerifyCurrentPassword === 'admin123') {
            showToast('✅ 본인 확인이 완료되었습니다.');
            setIsVerifySectionVisible(false);
        } else {
            showToast('❌ 아이디 또는 현재 비밀번호가 일치하지 않습니다.');
        }
    };

    const handleSubmitNewPassword = async () => {
        try {
            const token = localStorage.getItem('accessToken');
            const UserId = adminUser.LoginId;

            if (!token || UserId === 'Guest') {
                showToast("⚠️ 비밀번호 변경을 위해 로그인 상태를 확인해주세요.");
                return;
            }

            const response = await fetch(`${API_BASE_URL}/v1/users/${adminUser.id || 'admin'}`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ Password: passwordForm.NewPassword })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || "비밀번호 변경 실패.");
            }
            showToast('🔒 비밀번호가 성공적으로 변경되었습니다.');
            handleCloseModal();
        } catch (error) {
            showToast(`❌ 비밀번호 변경 중 오류: ${error.message}`);
        }
    };

    // ✅ Neuroglancer URL 생성 (로컬 API 사용)
    const getNeuroglancerUrl = async (volume) => {
        if (!volume) return '';
        
        try {
            const token = localStorage.getItem('accessToken');
            const response = await fetch(
                `${API_BASE_URL}/api/neuroglancer/state?volume_name=${volume.name}&location=${volume.location || 'tmp'}`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                }
            );
            
            if (response.ok) {
                const data = await response.json();
                // Docker 내부 URL을 로컬 URL로 변환
                return data.url.replace('http://neuroglancer:8080', 'http://localhost:8080');
            } else {
                console.error('Neuroglancer URL 생성 실패:', await response.text());
                return '';
            }
        } catch (error) {
            console.error('Neuroglancer URL 요청 에러:', error);
            return '';
        }
    };

    return (
        <div className="body-page admin-theme-wrapper">
            {/* 드로어 오버레이 */}
            <div
                id="drawerOverlay"
                className={`drawer-overlay ${isDrawerOpen ? 'overlay-visible' : ''}`}
                onClick={handleCloseDrawer}
            ></div>

            {/* 좌측 드로어 */}
            <div id="uploadDrawer" className={`upload-drawer ${isDrawerOpen ? 'drawer-visible' : ''}`}>
                <div className="drawer-header">
                    <h3>라이브러리 (Admin)</h3>
                </div>

                <div className="drawer-content" style={{ padding: 0 }}>

                    {/* ===== 섹션 1: 사진 관리 ===== */}
                    <div className="drawer-section">
                        <button
                            className="drawer-section-header"
                            onClick={() => setIsUploadSectionOpen(!isUploadSectionOpen)}
                        >
                            <span className="drawer-section-title">
                                <i className={`drawer-section-chevron ${isUploadSectionOpen ? 'open' : ''} fas fa-chevron-right`}></i>
                                <span>사진 관리</span>
                            </span>
                        </button>

                        {isUploadSectionOpen && (
                            <div className="drawer-section-body">
                                <div className="p-4">
                                    <Link
                                        to="/admin/file-select"
                                        className="w-full flex items-center justify-center px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium shadow-sm"
                                        onClick={handleCloseDrawer}
                                    >
                                        <i className="fas fa-images mr-2"></i>
                                        사진 선택하기
                                    </Link>
                                    <p className="text-xs text-gray-500 text-center mt-2">
                                        F:/uploads, /tmp/uploads, C:/uploads
                                    </p>
                                </div>

                                <div className="px-4 pb-4">
                                    <div className="relative">
                                        <div className="absolute inset-0 flex items-center">
                                            <div className="w-full border-t border-gray-200"></div>
                                        </div>
                                        <div className="relative flex justify-center text-xs">
                                            <span className="px-2 bg-white text-gray-500">또는 직접 업로드</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="px-4 pb-4">
                                    <div
                                        className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-blue-400 transition cursor-pointer"
                                        onDragOver={handleDragOver}
                                        onDragLeave={handleDragLeave}
                                        onDrop={handleFileDrop}
                                        onClick={() => fileInputRef.current.click()}
                                    >
                                        <i className="fas fa-cloud-upload-alt text-2xl text-gray-400 mb-1"></i>
                                        <p className="text-sm text-gray-600">클릭하여 파일 선택</p>
                                        <input
                                            type="file"
                                            multiple
                                            className="hidden"
                                            ref={fileInputRef}
                                            onChange={handleFileSelect}
                                            accept=".png,.jpg,.jpeg,.tiff,.tif"
                                        />
                                    </div>
                                </div>

                                {files.length > 0 && (
                                    <div className="px-4 pb-4">
                                        <div className="flex items-center justify-between mb-2">
                                            <h4 className="text-sm font-medium text-gray-700">
                                                업로드 대기 ({files.length})
                                            </h4>
                                            <button
                                                onClick={handleChunkConversion}
                                                disabled={uploading}
                                                className="px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 text-xs"
                                            >
                                                {uploading ? '변환 중...' : '청크 분해'}
                                            </button>
                                        </div>
                                        <div className="max-h-32 overflow-y-auto space-y-1">
                                            {files.map((file, index) => (
                                                <div key={index} className="flex items-center justify-between bg-gray-50 rounded p-2">
                                                    <div className="flex-1 min-w-0">
                                                        <p className="text-xs text-gray-700 truncate">{file.name}</p>
                                                        <p className="text-xs text-gray-500">
                                                            {(file.size / 1024 / 1024).toFixed(1)} MB
                                                        </p>
                                                    </div>
                                                    <button
                                                        onClick={() => handleDeleteFile(file)}
                                                        className="ml-2 text-red-500 hover:text-red-700"
                                                    >
                                                        <i className="fas fa-trash text-xs"></i>
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* ===== 섹션 2: 이미지 (Admin) ===== */}
                    <div className="drawer-section">
                        <button
                            className="drawer-section-header"
                            onClick={toggleMyImageSection}
                        >
                            <span className="drawer-section-title">
                                <i className={`drawer-section-chevron ${isMyImageSectionOpen ? 'open' : ''} fas fa-chevron-right`}></i>
                                <span>이미지 (Admin) ({volumes.length})</span>
                            </span>
                        </button>

                        {isMyImageSectionOpen && (
                            <div className="drawer-section-body">
                                {volumes.length === 0 ? (
                                    <p className="text-sm text-gray-400 text-center py-2">
                                        업로드된 이미지가 없습니다.
                                    </p>
                                ) : (
                                    <div className="volume-list">
                                        <div className="space-y-2 max-h-60 overflow-y-auto">
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
                                                            {volume.owner_login_id && (
                                                                <div className="volume-detail-item">
                                                                    <span className="volume-detail-label">소유자:</span>
                                                                    <span className="volume-detail-value">
                                                                        {volume.owner_login_id}
                                                                    </span>
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* ===== 섹션 3: 북마크 (Placeholder) ===== */}
                    <div className="drawer-section">
                        <button
                            className="drawer-section-header"
                            onClick={() => setIsBookmarkSectionOpen(!isBookmarkSectionOpen)}
                        >
                            <span className="drawer-section-title">
                                <i className={`drawer-section-chevron ${isBookmarkSectionOpen ? 'open' : ''} fas fa-chevron-right`}></i>
                                <span>북마크</span>
                            </span>
                        </button>
                        {isBookmarkSectionOpen && (
                            <div className="drawer-section-body min-h-[100px] flex items-center justify-center">
                                <p className="text-sm text-gray-400">저장된 북마크가 없습니다.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* 메인 컨테이너 */}
            <div className={`app-container ${isDrawerOpen ? 'drawer-open' : ''}`}>
                {/* 헤더 */}
                <header className="page-header">
                    <button id="hamburgerBtn" className="hamburger-btn" onClick={handleToggleDrawer}>
                        <i className="fas fa-bars"></i>
                    </button>
                    <h1 className="page-title">
                        <Link to="/">대용량 이미지 뷰어</Link>
                        <span className="ml-2 text-xs px-2 py-1 rounded-full bg-red-100 text-red-600 border border-red-300 align-middle">
                            ADMIN
                        </span>
                    </h1>
                    <div className="page-nav">
                        {adminUser.LoginId === 'Guest' ? (
                            <Link to="/login" id="loginBtn" className="header-login-btn">
                                <i className="fas fa-sign-in-alt"></i>
                                <span>로그인</span>
                            </Link>
                        ) : (
                            <div id="userProfileGroup" className="page-nav-group">
                                <div className={`header-user-rank ${RANK_DETAILS['Admin'].class}`}>
                                    <i className={RANK_DETAILS['Admin'].icon}></i>
                                    <span>{adminUser.rank}</span>
                                </div>
                                <span id="headerUserId" className="header-user-id">
                                    {adminUser.UserName || adminUser.LoginId}
                                </span>
                                <button className="profile-btn" onClick={handleOpenModal}>
                                    <img src={adminUser.profileImg} alt="프로필" id="mainProfileImg" />
                                </button>
                            </div>
                        )}
                    </div>
                </header>

                {/* ✅ Neuroglancer 뷰어 패널 (로컬 API 사용) */}
                <div className="main-content-area">
                    <div className="neuroglancer-panel">
                        <div className="neuroglancer-container" id="viewer3D">
                            {currentVolume && neuroglancerUrl ? (
                                <iframe
                                    key={currentVolume.name}
                                    title="Neuroglancer 뷰어"
                                    src={neuroglancerUrl}
                                    className="neuroglancer-iframe"
                                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                />
                            ) : (
                                <div className="flex items-center justify-center h-full bg-gray-100">
                                    <div className="text-center text-gray-500">
                                        <i className="fas fa-image text-6xl mb-4 opacity-30"></i>
                                        <p className="text-lg font-medium">이미지를 선택하거나 업로드하고</p>
                                        <p className="text-sm">청크 분해를 실행하세요 (Admin)</p>
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
                        <h2 className="modal-title">관리자 계정 관리</h2>
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
                                        <p className="form-note">보안을 위해 현재 관리자 정보를 확인합니다.</p>
                                        <div className="form-container">
                                            <div>
                                                <label htmlFor="VerifyId" className="form-label">현재 관리자 ID</label>
                                                <input
                                                    type="text"
                                                    id="VerifyId"
                                                    name="VerifyId"
                                                    className="input-field"
                                                    value={passwordForm.VerifyId}
                                                    onChange={handlePasswordFormChange}
                                                    readOnly
                                                />
                                            </div>
                                            <div>
                                                <label htmlFor="VerifyCurrentPassword" className="form-label">현재 비밀번호</label>
                                                <input
                                                    type="password"
                                                    id="VerifyCurrentPassword"
                                                    name="VerifyCurrentPassword"
                                                    className="input-field"
                                                    placeholder="현재 비밀번호"
                                                    value={passwordForm.VerifyCurrentPassword}
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
                                                <label htmlFor="NewPassword" className="form-label">새 비밀번호</label>
                                                <input
                                                    type="password"
                                                    id="NewPassword"
                                                    name="NewPassword"
                                                    placeholder="6자 이상 입력해주세요"
                                                    className="input-field"
                                                    value={passwordForm.NewPassword}
                                                    onChange={handlePasswordFormChange}
                                                />
                                            </div>
                                            <div>
                                                <label htmlFor="ConfirmPassword" className="form-label">비밀번호 확인</label>
                                                <input
                                                    type="password"
                                                    id="ConfirmPassword"
                                                    name="ConfirmPassword"
                                                    placeholder="다시 한번 입력해주세요"
                                                    className="input-field"
                                                    value={passwordForm.ConfirmPassword}
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
};

export default AdminPage;
