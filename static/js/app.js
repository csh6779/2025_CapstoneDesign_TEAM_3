// ========== 인증 관련 변수 ==========
let currentUser = null;
let authToken = null;
const defaultProfilePic = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="12" fill="%23adb5bd"/><path d="M12 4a4 4 0 100 8 4 4 0 000-8zM12 14c-4.42 0-8 3.58-8 8h16c0-4.42-3.58-8-8-8z" fill="%23f8f9fa"/></svg>';
const grades = ['bronze', 'silver', 'gold'];

// ========== Neuroglancer 관련 변수 ==========
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const uploadStatus = document.getElementById('uploadStatus');
const refreshBtn = document.getElementById('refreshBtn');
const volumesList = document.getElementById('volumesList');
const volumeSelect = document.getElementById('volumeSelect');

// ========== API 헬퍼 함수 ==========
function getAuthHeaders() {
    if (authToken) {
        return {
            'Authorization': `Bearer ${authToken}`
        };
    }
    return {};
}

async function apiCall(url, options = {}) {
    const headers = { ...getAuthHeaders(), ...options.headers };
    const response = await fetch(url, { ...options, headers });
    
    if (response.status === 401) {
        // 인증 만료 시 로그아웃
        if (currentUser) {
            alert('세션이 만료되었습니다. 다시 로그인해주세요.');
            handleLogout();
        }
        throw new Error('Unauthorized');
    }
    
    return response;
}

// ========== 인증 함수 ==========
function toggleAuthView(type) {
    document.getElementById('login-form').style.display = type === 'login' ? 'block' : 'none';
    document.getElementById('register-form').style.display = type === 'register' ? 'block' : 'none';
}

async function handleRegister() {
    const loginId = document.getElementById('reg-id').value;
    const password = document.getElementById('reg-password').value;
    const userName = document.getElementById('reg-name').value;
    const profileFileInput = document.getElementById('reg-profile-pic');
    const file = profileFileInput.files[0];

    if (!loginId || !password || !userName) {
        alert('아이디, 비밀번호, 이름을 입력해주세요.');
        return;
    }

    let userImageBase64 = null;

    // 프로필 사진이 선택된 경우 Base64로 변환
    if (file) {
        try {
            userImageBase64 = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (e) => resolve(e.target.result);
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
        } catch (error) {
            alert('프로필 사진 업로드 실패: ' + error.message);
            return;
        }
    }

    try {
        const response = await fetch('/v1/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                LoginId: loginId,
                Password: password,
                UserName: userName,
                Role: 'user',
                UserImage: userImageBase64  // Base64 문자열 또는 null
            })
        });

        if (response.ok) {
            alert('회원가입 성공! 로그인 해주세요.');
            toggleAuthView('login');
            document.getElementById('reg-id').value = '';
            document.getElementById('reg-password').value = '';
            document.getElementById('reg-name').value = '';
            profileFileInput.value = '';
        } else {
            const error = await response.json();
            console.error('회원가입 에러:', error);
            
            // 에러 메시지 상세 표시
            let errorMessage = '회원가입 실패\n\n';
            if (error.detail) {
                if (typeof error.detail === 'string') {
                    errorMessage += error.detail;
                } else if (Array.isArray(error.detail)) {
                    errorMessage += error.detail.map(e => `- ${e.msg || e.message || JSON.stringify(e)}`).join('\n');
                } else {
                    errorMessage += JSON.stringify(error.detail, null, 2);
                }
            } else {
                errorMessage += JSON.stringify(error, null, 2);
            }
            
            alert(errorMessage);
        }
    } catch (error) {
        alert(`회원가입 실패: ${error.message}`);
    }
}

async function handleLogin() {
    const loginId = document.getElementById('login-id').value;
    const password = document.getElementById('login-password').value;

    if (!loginId || !password) {
        alert('아이디와 비밀번호를 입력해주세요.');
        return;
    }

    try {
        // FormData로 로그인 요청
        const formData = new URLSearchParams();
        formData.append('username', loginId);
        formData.append('password', password);

        const response = await fetch('/v1/auth/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            authToken = data.AccessToken;
            
            // 사용자 정보 가져오기
            const userResponse = await apiCall('/v1/auth/me');
            const userData = await userResponse.json();
            
            // 랜덤 등급 부여 (또는 실제 등급 사용)
            const randomGrade = grades[Math.floor(Math.random() * grades.length)];
            
            currentUser = {
                id: userData.id,
                loginId: userData.LoginId,
                name: userData.UserName,
                role: userData.Role,
                profilePic: userData.UserImage || defaultProfilePic,  // Base64 또는 기본 이미지
                grade: randomGrade
            };

            alert(`${currentUser.name}님, 환영합니다!`);
            showMainView();
        } else {
            const error = await response.json();
            alert(`로그인 실패: ${error.detail || '아이디 또는 비밀번호가 올바르지 않습니다.'}`);
        }
    } catch (error) {
        alert(`로그인 실패: ${error.message}`);
    }
}

function handleLogout() {
    currentUser = null;
    authToken = null;
    document.getElementById('main-view').style.display = 'none';
    document.getElementById('auth-view').style.display = 'block';
    alert('로그아웃 되었습니다.');
}

function showMainView() {
    if (!currentUser) {
        alert('로그인이 필요합니다.');
        return;
    }

    document.getElementById('user-profile-pic').src = currentUser.profilePic || defaultProfilePic;
    const gradeElement = document.getElementById('user-grade');
    gradeElement.textContent = currentUser.grade.toUpperCase();
    gradeElement.className = `grade ${currentUser.grade.toLowerCase()}`;

    document.getElementById('auth-view').style.display = 'none';
    document.getElementById('main-view').style.display = 'block';

    loadVolumes();
    refreshMemoryStats();
}

// ========== Neuroglancer 업로드 기능 ==========
fileInput.addEventListener('change', () => {
    uploadBtn.disabled = !fileInput.files.length;
});

uploadBtn.addEventListener('click', async () => {
    const file = fileInput.files[0];
    if (!file) return;

    uploadBtn.disabled = true;
    uploadStatus.innerHTML = '<div class="status info">업로드 중...</div>';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await apiCall('/api/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            uploadStatus.innerHTML = `<div class="status success">${result.message}</div>`;
            fileInput.value = '';
            uploadBtn.disabled = true;
            loadVolumes();
            refreshMemoryStats();
        } else {
            uploadStatus.innerHTML = `<div class="status error">에러: ${result.detail}</div>`;
        }
    } catch (error) {
        uploadStatus.innerHTML = `<div class="status error">업로드 실패: ${error.message}</div>`;
    } finally {
        uploadBtn.disabled = false;
    }
});

// ========== 메모리 관리 ==========
async function refreshMemoryStats() {
    if (!authToken) return; // 로그인하지 않은 경우 스킵
    
    try {
        const response = await apiCall('/api/memory-status');
        const stats = await response.json();

        document.getElementById('serverMemory').textContent =
            `${stats.memory.process_mb.toFixed(1)}MB (${stats.memory.system_percent.toFixed(1)}%)`;

        document.getElementById('cacheUsage').textContent =
            `${stats.cache.cache_size_mb.toFixed(1)}MB / ${stats.config.cache_max_size_mb}MB`;

        document.getElementById('cacheHitRate').textContent =
            `${(stats.cache.hit_rate * 100).toFixed(1)}%`;

    } catch (error) {
        console.error('메모리 상태 조회 실패:', error);
    }
}

async function cleanupMemory() {
    try {
        const response = await apiCall('/api/memory-cleanup', {method: 'POST'});
        const result = await response.json();

        alert(`메모리 정리 완료: ${result.freed_mb.toFixed(1)}MB 해제`);
        refreshMemoryStats();

    } catch (error) {
        alert('메모리 정리 실패: ' + error.message);
    }
}

// ========== 볼륨 관리 ==========
function updateVolumeSelect(volumes) {
    volumeSelect.innerHTML = '<option value="">볼륨을 선택하세요</option>' +
        volumes.map(volume => `<option value="${volume.name}">${volume.name}</option>`).join('');
}

async function deleteVolume(volumeName) {
    if (!confirm(`볼륨 '${volumeName}'을 삭제하시겠습니까?`)) return;

    try {
        const response = await apiCall(`/api/volumes/${volumeName}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (response.ok) {
            alert(result.message);
            loadVolumes();
        } else {
            alert(`삭제 실패: ${result.detail}`);
        }
    } catch (error) {
        alert(`삭제 실패: ${error.message}`);
    }
}

function copyToClipboard(text, buttonElement) {
    navigator.clipboard.writeText(text).then(() => {
        const originalText = buttonElement.textContent;
        const originalClass = buttonElement.className;

        buttonElement.textContent = '복사됨!';
        buttonElement.classList.add('copy-success');

        setTimeout(() => {
            buttonElement.textContent = originalText;
            buttonElement.className = originalClass;
        }, 2000);
    }).catch(err => {
        console.error('복사 실패:', err);
        alert('URL 복사 완료!');
    });
}

function openNeuroglancer(username, volumeName) {
    // uploads 경로 사용: /uploads/{username}/{volumeName}
    const sourceUrl = `precomputed://http://localhost:8000/uploads/${username}/${volumeName}`;
    const neuroglancerConfig = {
        "layers": [
            {
                "type": "image",
                "source": sourceUrl,
                "name": volumeName,
                "blend": "default"
            }
        ],
        "navigation": {
            "pose": {
                "position": {
                    "voxelSize": [1, 1, 1]
                }
            },
            "zoomFactor": 8
        },
        "showSlices": false,
        "layout": "4panel"
    };

    const configString = JSON.stringify(neuroglancerConfig);
    const encodedConfig = encodeURIComponent(configString);
    const neuroglancerUrl = `https://neuroglancer-demo.appspot.com/#!${encodedConfig}`;

    window.open(neuroglancerUrl, '_blank');
}

async function loadVolumes() {
    if (!authToken) return; // 로그인하지 않은 경우 스킵

    try {
        const response = await apiCall('/api/volumes');
        const result = await response.json();

        if (response.ok) {
            displayVolumes(result.volumes);
            updateVolumeSelect(result.volumes);
        }
    } catch (error) {
        console.error('볼륨 목록 로드 실패:', error);
    }
}

function displayVolumes(volumes) {
    if (volumes.length === 0) {
        volumesList.innerHTML = '<p class="small">아직 변환된 볼륨이 없습니다. 위에서 이미지를 업로드해보세요!</p>';
        return;
    }

    volumesList.innerHTML = volumes.map(volume => {
        // 서버에서 보내준 URL 사용 (이미 올바른 /uploads/{username}/{volumeName} 형식)
        const sourceUrl = volume.neuroglancer_url;
        const username = volume.username || currentUser.name;

        const neuroglancerConfig = {
            "layers": [{
                "type": "image",
                "source": sourceUrl,
                "name": volume.name,
                "blend": "default"
            }],
            "navigation": {
                "pose": {"position": {"voxelSize": [1, 1, 1]}},
                "zoomFactor": 8
            },
            "showSlices": false,
            "layout": "4panel"
        };

        const configString = JSON.stringify(neuroglancerConfig);
        const encodedConfig = encodeURIComponent(configString);
        const neuroglancerUrl = `https://neuroglancer-demo.appspot.com/#!${encodedConfig}`;

        return `
            <div class="volume-item">
                <div class="volume-header">
                    <div class="volume-info">
                        <strong>📊 ${volume.name}</strong>
                    </div>
                </div>

                <div class="url-section">
                    <strong>Precomputed 소스 URL:</strong>
                    <input type="text" class="url-input" value="${sourceUrl}" readonly>
                    <button onclick="copyToClipboard('${sourceUrl}', this)" class="btn btn-warning">
                        📋 소스 URL 복사
                    </button>
                </div>

                <div class="url-section">
                    <strong>Neuroglancer 직접 링크:</strong>
                    <input type="text" class="url-input" value="${neuroglancerUrl}" readonly>
                    <button onclick="copyToClipboard('${neuroglancerUrl}', this)" class="btn btn-info">
                        🔗 Neuroglancer URL 복사
                    </button>
                </div>

                <div class="volume-actions">
                    <button onclick="openNeuroglancer('${username}', '${volume.name}')" class="btn btn-neuroglancer">
                        🧠 Neuroglancer에서 열기
                    </button>
                    <a href="${volume.info_url || '/uploads/' + username + '/' + volume.name + '/info'}" target="_blank" class="btn btn-primary">📋 Info 보기</a>
                    <button onclick="deleteVolume('${volume.name}')" class="btn btn-danger">🗑️ 삭제</button>
                </div>
            </div>
        `;
    }).join('');
}

// ========== 로그 관리 ==========
async function viewLogs(logType = 'main') {
    try {
        const response = await apiCall(`/api/logs/recent?log_type=${logType}&lines=100`);
        const result = await response.json();

        if (response.ok && result.logs.length > 0) {
            const logWindow = window.open('', '_blank', 'width=1000,height=600');
            logWindow.document.write(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>로그 보기 - ${logType}</title>
                    <style>
                        body {
                            font-family: 'Consolas', 'Monaco', monospace;
                            background: #1e1e1e;
                            color: #d4d4d4;
                            padding: 20px;
                            margin: 0;
                        }
                        h2 {
                            color: #4ec9b0;
                            border-bottom: 2px solid #4ec9b0;
                            padding-bottom: 10px;
                        }
                        .log-line {
                            padding: 4px 0;
                            border-bottom: 1px solid #333;
                            font-size: 13px;
                            line-height: 1.6;
                        }
                        .log-line:hover {
                            background: #2d2d2d;
                        }
                        .info { color: #4ec9b0; }
                        .error { color: #f48771; }
                        .warning { color: #ce9178; }
                        .debug { color: #9cdcfe; }
                    </style>
                </head>
                <body>
                    <h2>📝 로그 보기: ${logType.toUpperCase()}</h2>
                    <p>전체 ${result.total_lines}줄 중 최근 ${result.returned_lines}줄</p>
                    <div>
                        ${result.logs.map(line => {
                            let className = 'log-line';
                            if (line.includes('ERROR')) className += ' error';
                            else if (line.includes('WARNING')) className += ' warning';
                            else if (line.includes('DEBUG')) className += ' debug';
                            else if (line.includes('INFO')) className += ' info';
                            return `<div class="${className}">${line}</div>`;
                        }).join('')}
                    </div>
                </body>
                </html>
            `);
        } else {
            alert(`${logType} 로그가 없거나 비어있습니다.`);
        }
    } catch (error) {
        alert(`로그 조회 실패: ${error.message}`);
    }
}

// ========== 타일 테스트 ==========
let volumeInfo = null;

async function loadVolumeInfo(username, volumeName) {
    try {
        // uploads 경로 사용
        const response = await fetch(`/uploads/${username}/${volumeName}/info`);
        if (response.ok) {
            volumeInfo = await response.json();
            return volumeInfo;
        }
    } catch (error) {
        console.error('볼륨 정보 로드 실패:', error);
    }
    return null;
}

const TILE_PATTERN = (username, volume, lvl, x, y, z = 0) => {
    // uploads 경로 사용: /uploads/{username}/{volume}/{level}/{x}_{y}_{z}
    return `/uploads/${username}/${volume}/${lvl}/${x}_${y}_${z}`;
};

async function fetchTile(url, idx) {
    const t0 = performance.now();
    try {
        const resp = await fetch(url);
        const buf = await resp.arrayBuffer();
        const t1 = performance.now();
        return {
            ok: resp.ok,
            status: resp.status,
            bytes: buf.byteLength,
            ms: Math.round(t1 - t0),
            url,
            idx
        };
    } catch (e) {
        const t1 = performance.now();
        return { ok: false, status: "ERR", bytes: 0, ms: Math.round(t1 - t0), url, idx };
    }
}

function renderRow(res) {
    const tr = document.createElement("tr");
    tr.className = res.ok ? "rowok" : "rowng";
    tr.innerHTML = `
        <td>${res.idx + 1}</td>
        <td class="small"><code>${res.url}</code></td>
        <td>${res.ok ? `<span class="ok">${res.status}</span>` : `<span class="ng">${res.status}</span>`}</td>
        <td>${res.bytes}</td>
        <td>${res.ms}</td>
    `;
    document.getElementById("tbody").appendChild(tr);
}

document.getElementById("startBtn").addEventListener("click", async () => {
    const volume = volumeSelect.value;
    if (!volume) {
        alert('볼륨을 선택해주세요.');
        return;
    }

    const username = currentUser.name;  // 또는 currentUser.loginId
    await loadVolumeInfo(username, volume);
    const level = document.getElementById("level").value.trim();
    const count = parseInt(document.getElementById("count").value, 10);
    document.getElementById("tbody").innerHTML = "";

    const tasks = [];
    let x = 0, y = 0;
    for (let i = 0; i < count; i++) {
        const url = TILE_PATTERN(username, volume, level, x, y, 0);
        tasks.push(fetchTile(url, i));
        x++;
        if (x >= 4) { x = 0; y++; }
    }

    const results = await Promise.all(tasks);
    results.forEach(renderRow);
});

// ========== 새로고침 버튼 ==========
refreshBtn.addEventListener('click', loadVolumes);

// ========== 초기화 ==========
document.addEventListener('DOMContentLoaded', () => {
    // 로그인 화면으로 시작
    toggleAuthView('login');

    // 메인 화면 숨기기
    document.getElementById('main-view').style.display = 'none';
    document.getElementById('auth-view').style.display = 'block';
});

// 5초마다 메모리 상태 업데이트 (로그인 후에만)
setInterval(() => {
    if (currentUser && authToken && document.getElementById('main-view').style.display !== 'none') {
        refreshMemoryStats();
    }
}, 5000);