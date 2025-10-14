// ========== 인증 관련 변수 ==========
let currentUser = null;
const userDatabase = {};
const defaultProfilePic = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="12" fill="%23adb5bd"/><path d="M12 4a4 4 0 100 8 4 4 0 000-8zM12 14c-4.42 0-8 3.58-8 8h16c0-4.42-3.58-8-8-8z" fill="%23f8f9fa"/></svg>';
const grades = ['bronze', 'silver', 'gold'];

// ========== Neuroglancer 관련 변수 ==========
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const uploadStatus = document.getElementById('uploadStatus');
const refreshBtn = document.getElementById('refreshBtn');
const volumesList = document.getElementById('volumesList');
const volumeSelect = document.getElementById('volumeSelect');

// ========== 인증 함수 ==========
function toggleAuthView(type) {
    document.getElementById('login-form').style.display = type === 'login' ? 'block' : 'none';
    document.getElementById('register-form').style.display = type === 'register' ? 'block' : 'none';
}

function handleRegister() {
    const id = document.getElementById('reg-id').value;
    const password = document.getElementById('reg-password').value;
    const name = document.getElementById('reg-name').value;
    const profileFileInput = document.getElementById('reg-profile-pic');
    const file = profileFileInput.files[0];

    if (!id || !password || !name || !file) {
        alert('모든 정보를 입력하고 프로필 사진을 선택해 주세요.');
        return;
    }

    if (userDatabase[id]) {
        alert('이미 존재하는 아이디입니다.');
        return;
    }

    const reader = new FileReader();
    reader.onload = function(e) {
        userDatabase[id] = {
            password: password,
            name: name,
            profilePic: e.target.result,
            grade: 'bronze'
        };
        alert('회원가입 성공! 로그인 해주세요.');
        toggleAuthView('login');
        document.getElementById('reg-id').value = '';
        document.getElementById('reg-password').value = '';
        document.getElementById('reg-name').value = '';
        profileFileInput.value = '';
    };
    reader.readAsDataURL(file);
}

function handleLogin() {
    const id = document.getElementById('login-id').value;
    const password = document.getElementById('login-password').value;

    if (userDatabase[id] && userDatabase[id].password === password) {
        const randomGrade = grades[Math.floor(Math.random() * grades.length)];

        currentUser = {
            id: id,
            name: userDatabase[id].name,
            profilePic: userDatabase[id].profilePic,
            grade: randomGrade
        };

        alert(`${currentUser.name}님, 환영합니다!`);
        showMainView();
    } else {
        alert('아이디 또는 비밀번호가 올바르지 않습니다.');
    }
}

function handleLogout() {
    currentUser = null;
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
        const response = await fetch('/api/upload', {
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
    try {
        const response = await fetch('/api/memory-status');
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
        const response = await fetch('/api/memory-cleanup', {method: 'POST'});
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
        const response = await fetch(`/api/volumes/${volumeName}`, {
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
        alert('URL이 복사되었습니다!');
    });
}

function openNeuroglancer(volumeName) {
    const sourceUrl = `precomputed://http://localhost:8000/precomp/${volumeName}`;
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
    try {
        const response = await fetch('/api/volumes');
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
        const sourceUrl = `precomputed://http://localhost:8000/precomp/${volume.name}`;
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
                    <button onclick="openNeuroglancer('${volume.name}')" class="btn btn-neuroglancer">
                        🧠 Neuroglancer에서 열기
                    </button>
                    <a href="${volume.path}/info" target="_blank" class="btn btn-primary">📋 Info 보기</a>
                    <button onclick="deleteVolume('${volume.name}')" class="btn btn-danger">🗑️ 삭제</button>
                </div>
            </div>
        `;
    }).join('');
}

// ========== 로그 관리 ==========
async function viewLogs(logType = 'main') {
    try {
        const response = await fetch(`/api/logs/recent?log_type=${logType}&lines=100`);
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

async function loadVolumeInfo(volumeName) {
    try {
        const response = await fetch(`/precomp/${volumeName}/info`);
        if (response.ok) {
            volumeInfo = await response.json();
            return volumeInfo;
        }
    } catch (error) {
        console.error('볼륨 정보 로드 실패:', error);
    }
    return null;
}

const TILE_PATTERN = (volume, lvl, x, y, z = 0) => {
    return `/precomp/${volume}/${x}_${y}_${z}/${lvl}`;
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

    await loadVolumeInfo(volume);
    const level = document.getElementById("level").value.trim();
    const count = parseInt(document.getElementById("count").value, 10);
    document.getElementById("tbody").innerHTML = "";

    const tasks = [];
    let x = 0, y = 0;
    for (let i = 0; i < count; i++) {
        const url = TILE_PATTERN(volume, level, x, y, 0);
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
    toggleAuthView('login');
});

// 5초마다 메모리 상태 업데이트 (로그인 후에만)
setInterval(() => {
    if (currentUser && document.getElementById('main-view').style.display !== 'none') {
        refreshMemoryStats();
    }
}, 5000);
