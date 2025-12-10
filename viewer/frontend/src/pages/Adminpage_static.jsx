import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import "../Adminpage_static.css";

// ✅ [수정] 백엔드 주소 상수 정의
const API_BASE_URL = 'http://localhost:9000';

// ✅ [수정] 타일 요청도 백엔드(9000번)로 향하도록 수정
const TILE_PATTERN = (volume, lvl, x, y, z = 0) =>
  `${API_BASE_URL}/precomp/${volume}/${x}_${y}_${z}/${lvl}`;

function Adminpage_static() {
  const navigate = useNavigate();

  // --- 기존 State ---
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState({
    type: null,
    message: "",
  });

  const [memoryInfo, setMemoryInfo] = useState({
    serverMemory: "로딩 중...",
    cacheUsage: "로딩 중...",
    cacheHitRate: "로딩 중...",
  });

  const [volumes, setVolumes] = useState([]);
  const [selectedVolume, setSelectedVolume] = useState("");
  const [level, setLevel] = useState("0");
  const [count, setCount] = useState(8);
  const [tileResults, setTileResults] = useState([]);

  const copyTimeoutRef = useRef(null);

  // 관리자 정보 State
  const [adminUser, setAdminUser] = useState({
    name: '관리자',
    role: ''
  });

  // 초기화 및 권한 체크
  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    const role = (localStorage.getItem('Role') || '').toLowerCase();

    // 1. 토큰이 없거나 관리자가 아니면 로그인 페이지로 강제 이동
    if (!token || role !== 'admin') {
      alert('관리자 권한이 필요합니다. 관리자 계정으로 로그인해주세요.');
      navigate('/login');
      return;
    }

    // 2. 관리자 정보 세팅
    const storedUserName = localStorage.getItem('UserName') || '관리자';
    setAdminUser({ name: storedUserName, role: role });

    // 3. 데이터 로드
    loadVolumes();
    refreshMemoryStats();
    const id = setInterval(refreshMemoryStats, 5000);

    return () => {
      clearInterval(id);
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate]);

  // 로그아웃 핸들러
  const handleLogout = () => {
    if (window.confirm("정말 로그아웃 하시겠습니까?")) {
      localStorage.clear();
      alert("로그아웃되었습니다.");
      navigate('/login');
    }
  };

  // ----- 로직 (API 경로 수정됨) -----
  const handleFileChange = (e) => {
    const file = e.target.files?.[0] || null;
    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadStatus({ type: "info", message: "업로드 중..." });

    const formData = new FormData();
    formData.append("file", selectedFile);

    const token = localStorage.getItem('accessToken');

    try {
      // ✅ [수정] API_BASE_URL 추가
      const response = await fetch(`${API_BASE_URL}/api/v1/upload`, {
        method: "POST",
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData,
      });
      const result = await response.json();

      if (response.ok) {
        setUploadStatus({ type: "success", message: result.message || "업로드 완료" });
        setSelectedFile(null);
        await loadVolumes();
        await refreshMemoryStats();
      } else {
        setUploadStatus({ type: "error", message: `에러: ${result.detail || response.status}` });
      }
    } catch (e) {
      setUploadStatus({ type: "error", message: `업로드 실패: ${e.message}` });
    } finally {
      setIsUploading(false);
    }
  };

  const refreshMemoryStats = async () => {
    try {
      // ✅ [수정] API_BASE_URL 추가
      const r = await fetch(`${API_BASE_URL}/api/v1/memory-status`, { cache: "no-store" });

      if (!r.ok) {
        throw new Error(`Server returned ${r.status}`);
      }

      const s = await r.json();

      setMemoryInfo({
        serverMemory: `${s.memory.process_mb.toFixed(1)}MB (${s.memory.system_percent.toFixed(1)}%)`,
        cacheUsage: `${s.cache.cache_size_mb.toFixed(1)}MB / ${s.config.cache_max_size_mb}MB`,
        cacheHitRate: `${(s.cache.hit_rate * 100).toFixed(1)}%`,
      });
    } catch (e) {
      console.error("메모리 상태 조회 실패:", e);
      // 에러 발생 시 UI가 깨지지 않도록 기본값 유지 혹은 에러 표시
    }
  };

  const cleanupMemory = async () => {
    try {
      const token = localStorage.getItem('accessToken');
      // ✅ [수정] API_BASE_URL 추가
      const r = await fetch(`${API_BASE_URL}/api/v1/memory-clean`, {
        method: "POST",
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const j = await r.json();
      alert(`메모리 정리 완료: ${j.freed_mb.toFixed(1)}MB 해제`);
      refreshMemoryStats();
    } catch (e) {
      alert("메모리 정리 실패: " + e.message);
    }
  };

  const normalizeVolumesResponse = (data) => {
    if (Array.isArray(data)) return data;
    if (data?.items) return data.items;
    if (data?.volumes) return data.volumes;
    return [];
  };

  const loadVolumes = async () => {
    try {
      const token = localStorage.getItem('accessToken');
      // ✅ [수정] API_BASE_URL 추가
      const res = await fetch(`${API_BASE_URL}/api/admin/volumes`, {
        cache: "no-store",
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      const list = normalizeVolumesResponse(data);
      setVolumes(list);
    } catch (error) {
      console.error("볼륨 목록 로드 실패:", error);
      setVolumes([]);
    }
  };

  // ✅ Neuroglancer URL 생성 (로컬 API 사용)
  const buildNgUrl = async (name, location) => {
    try {
      const token = localStorage.getItem('accessToken');
      const response = await fetch(
        `${API_BASE_URL}/api/neuroglancer/state?volume_name=${name}&location=${location || 'tmp'}`,
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

  // ✅ 새 창에서 Neuroglancer 열기 (로컬 서버 사용)
  const openNeuroglancer = async (name, location) => {
    const url = await buildNgUrl(name, location);
    if (url) {
      window.open(url, "_blank");
    } else {
      alert('Neuroglancer URL 생성에 실패했습니다.');
    }
  };

  const deleteVolume = async (volumeName) => {
    if (!window.confirm(`볼륨 '${volumeName}'을 삭제하시겠습니까?`)) return;
    try {
      const token = localStorage.getItem('accessToken');

      const r = await fetch(`${API_BASE_URL}/api/admin/volumes/${volumeName}`, {
        method: "DELETE",
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const j = await r.json();
      if (r.ok) {
        alert(j.message || "삭제 완료");
        loadVolumes(); // 목록 새로고침
      } else {
        alert(`삭제 실패: ${j.detail || r.status}`);
      }
    } catch (e) {
      alert(`삭제 실패: ${e.message}`);
    }
  };

  const loadVolumeInfo = async (volumeName) => {
    try {
      // ✅ [수정] API_BASE_URL 추가 (Info 요청도 백엔드로)
      const r = await fetch(`${API_BASE_URL}/precomp/${volumeName}/info`, { cache: "no-store" });
      if (r.ok) return await r.json();
    } catch (e) {
      console.error("볼륨 정보 로드 실패:", e);
    }
    return null;
  };

  const fetchTile = async (url, idx) => {
    const t0 = performance.now();
    try {
      const resp = await fetch(url, { cache: "no-store" });
      const buf = await resp.arrayBuffer();
      const t1 = performance.now();
      return { ok: resp.ok, status: resp.status, bytes: buf.byteLength, ms: Math.round(t1 - t0), url, idx };
    } catch (e) {
      const t1 = performance.now();
      return { ok: false, status: "ERR", bytes: 0, ms: Math.round(t1 - t0), url, idx };
    }
  };

  const handleFetchTiles = async () => {
    if (!selectedVolume) {
      alert("볼륨을 선택해주세요.");
      return;
    }
    await loadVolumeInfo(selectedVolume);
    const trimmedLevel = String(level).trim();
    const countNum = parseInt(count, 10);
    if (!Number.isFinite(countNum) || countNum <= 0) {
      alert("Fetch count는 1 이상의 숫자여야 합니다.");
      return;
    }
    setTileResults([]);
    const tasks = [];
    let x = 0; let y = 0;
    for (let i = 0; i < countNum; i += 1) {
      const url = TILE_PATTERN(selectedVolume, trimmedLevel, x, y, 0);
      tasks.push(fetchTile(url, i));
      x += 1;
      if (x >= 4) { x = 0; y += 1; }
    }
    const results = await Promise.all(tasks);
    results.sort((a, b) => a.idx - b.idx);
    setTileResults(results);
  };

  const normalizedVolumes = (volumes || []).map((v) =>
    typeof v === "string" ? { name: v } : v
  );

  const renderUploadStatus = () => {
    if (!uploadStatus.type) return null;
    return <div className={`status ${uploadStatus.type}`}>{uploadStatus.message}</div>;
  };

  return (
    <div style={{ margin: "20px" }}>
      {/* 상단 헤더: 제목 + 사용자 정보 + 로그아웃 버튼 */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px',
        borderBottom: '1px solid #eee',
        paddingBottom: '10px'
      }}>
        <div className="header-title">
          <h1 style={{ margin: 0, fontSize: '24px' }}>ATI NEURO</h1>
          <span className="badge" style={{ backgroundColor: '#dc3545', color: '#fff', marginLeft: '10px' }}>Admin</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <span style={{ fontWeight: 'bold' }}>
            <i className="fas fa-user-shield" style={{ marginRight: '5px' }}></i>
            {adminUser.name} ({adminUser.role})
          </span>
          <button
            onClick={handleLogout}
            style={{
              padding: '8px 16px',
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            로그아웃
          </button>
        </div>
      </div>

      <p className="small">
        이미지를 업로드하면 자동으로 청크로 변환되어 Neuroglancer에서 볼 수 있습니다.
      </p>

      {/* 파일 업로드 */}
      <div className="upload-section">
        <h3>📁 이미지 업로드</h3>
        <p className="small">
          PNG, JPG, TIFF, BMP 형식의 이미지를 업로드하면 자동으로 Neuroglancer 호환 청크로 변환됩니다.
        </p>
        <div className="file-input">
          <input
            type="file"
            accept=".png,.jpg,.jpeg,.tiff,.tif,.bmp"
            onChange={handleFileChange}
          />
        </div>
        <button
          type="button"
          className="upload-btn"
          onClick={handleUpload}
          disabled={!selectedFile || isUploading}
        >
          {isUploading ? "업로드 중..." : "업로드 및 청크 변환"}
        </button>
        <div id="uploadStatus">{renderUploadStatus()}</div>
      </div>

      {/* 메모리 상태 */}
      <div className="memory-section">
        <h3>🧠 메모리 상태</h3>
        <div id="memoryInfo">
          <div>
            서버 메모리: <span id="serverMemory">{memoryInfo.serverMemory}</span>
          </div>
          <div>
            캐시 사용량: <span id="cacheUsage">{memoryInfo.cacheUsage}</span>
          </div>
          <div>
            처리 효율성: <span id="cacheHitRate">{memoryInfo.cacheHitRate}</span>
          </div>
        </div>
        <div className="memory-controls">
          <button type="button" onClick={refreshMemoryStats} className="btn btn-primary">새로고침</button>
          <button type="button" onClick={cleanupMemory} className="btn btn-success">메모리 정리</button>
        </div>
      </div>

      {/* 변환된 볼륨 목록 */}
      <div className="volumes-section">
        <h3>📊 변환된 볼륨 목록</h3>
        <p className="small">업로드하여 변환된 이미지들을 Neuroglancer에서 볼 수 있습니다.</p>
        <button type="button" id="refreshBtn" className="btn btn-primary" onClick={loadVolumes}>새로고침</button>
        <div id="volumesList">
          {normalizedVolumes.length === 0 ? (
            <p className="small">아직 변환된 볼륨이 없습니다. 위에서 이미지를 업로드해보세요!</p>
          ) : (
            normalizedVolumes.map((volume) => {
              const name = volume.name || volume;
              const infoHref = volume.info_url || `${API_BASE_URL}/precomp/${name}/info`;

              const meta = {
                enc: volume.encoding || "raw",
                dtype: volume.data_type || "-",
                size: Array.isArray(volume.size) ? volume.size.join("×") : "-",
                chunk: Array.isArray(volume.chunk_size) ? volume.chunk_size.join("×") : "-",
                c: volume.num_channels === 0 ? 0 : volume.num_channels ?? "-",
              };

              return (
                <div key={`${volume.location}-${name}`} className="volume-item">
                  <div className="volume-header">
                    <div className="volume-info">
                      <strong>📊 {name} <span style={{ fontSize: '0.8em', color: '#666' }}>({volume.location})</span></strong>
                      <div className="badges">
                        <span className="badge">enc: {meta.enc}</span>
                        <span className="badge">dtype: {meta.dtype}</span>
                        <span className="badge">channels: {meta.c}</span>
                        <span className="badge">size: {meta.size}</span>
                        <span className="badge warn">chunk: {meta.chunk}</span>
                      </div>
                    </div>
                  </div>

                  {/* ✅ URL 섹션 제거됨 */}

                  <div className="volume-actions">
                    <button 
                      type="button" 
                      onClick={() => openNeuroglancer(name, volume.location)} 
                      className="btn btn-neuroglancer"
                    >
                      🧠 Neuroglancer에서 열기
                    </button>
                    <a href={infoHref} target="_blank" rel="noreferrer" className="btn btn-primary">📋 Info 보기</a>
                    <button type="button" onClick={() => deleteVolume(name)} className="btn btn-danger">🗑️ 삭제</button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* 타일 테스트 */}
      <div className="volumes-section">
        <h3>🧪 타일 테스트</h3>
        <p className="small">변환된 볼륨의 개별 타일을 테스트합니다.</p>
        <div id="controls">
          <label>
            볼륨 선택:{" "}
            <select id="volumeSelect" value={selectedVolume} onChange={(e) => setSelectedVolume(e.target.value)}>
              <option value="">볼륨을 선택하세요</option>
              {normalizedVolumes.map((v) => {
                const name = v.name || v;
                return (
                  <option key={`${v.location}-${name}`} value={name}>
                    {name} ({v.location})
                  </option>
                );
              })}
            </select>
          </label>
          <label>Level key: <input id="level" type="text" value={level} onChange={(e) => setLevel(e.target.value)} /></label>
          <label>Fetch count (tiles): <input id="count" type="number" value={count} min={1} onChange={(e) => setCount(Number(e.target.value))} /></label>
          <button type="button" id="startBtn" className="btn btn-primary" onClick={handleFetchTiles}>Fetch tiles</button>
        </div>

        <table>
          <thead>
            <tr><th>#</th><th>URL</th><th>Status</th><th>Bytes</th><th>Time (ms)</th></tr>
          </thead>
          <tbody id="tbody">
            {tileResults.map((res) => (
              <tr key={res.idx} className={res.ok ? "rowok" : "rowng"}>
                <td>{res.idx + 1}</td>
                <td className="small"><code>{res.url}</code></td>
                <td>{res.ok ? <span className="ok">{res.status}</span> : <span className="ng">{res.status}</span>}</td>
                <td>{res.bytes}</td>
                <td>{res.ms}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Adminpage_static;
