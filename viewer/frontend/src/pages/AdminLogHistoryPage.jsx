import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:9000';

function AdminLogHistoryPage() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // ✅ 필터 상태
    const [filter, setFilter] = useState({
        days: 7,
        logLevel: '',
        searchKeyword: '', // 파일명/경로 검색
        targetUser: ''     // ✅ 사용자 ID 검색 필터 추가
    });

    const navigate = useNavigate();

    useEffect(() => {
        const token = localStorage.getItem('accessToken');
        // 권한 체크 로직 (간단하게 로컬 스토리지로 1차 방어)
        /* const role = localStorage.getItem('userRole'); // 로그인 시 저장 필요
        if (!token || role !== 'admin') {
             alert('관리자 권한이 필요합니다.');
             navigate('/');
             return;
        }
        */
        if (!token) {
            navigate('/login');
            return;
        }
        fetchLogs();
    }, [filter.days, filter.logLevel]); // 날짜/레벨 변경 시 자동 조회

    const fetchLogs = async () => {
        setLoading(true);
        setError(null);

        try {
            const token = localStorage.getItem('accessToken');

            const endDate = new Date();
            const startDate = new Date();
            if (filter.days > 0) {
                startDate.setDate(endDate.getDate() - filter.days);
            } else {
                startDate.setFullYear(2020);
            }

            const params = new URLSearchParams({
                skip: 0,
                limit: 500, // 관리자는 더 많이 보기
                start_date: startDate.toISOString().split('T')[0],
                end_date: endDate.toISOString().split('T')[0]
            });

            if (filter.logLevel) params.append('level', filter.logLevel);
            if (filter.targetUser) params.append('target_user_id', filter.targetUser); // ✅ 사용자 필터 전송

            // ✅ 관리자용 API 호출 (/all)
            const response = await fetch(`${API_BASE_URL}/api/v1/image-logs/all?${params}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) {
                if (response.status === 403) throw new Error('관리자 권한이 없습니다.');
                const errorData = await response.json();
                throw new Error(errorData.detail || '로그 조회 실패');
            }

            const data = await response.json();

            let fetchedLogs = [];
            if (Array.isArray(data)) fetchedLogs = data;
            else if (data.logs) fetchedLogs = data.logs;

            // 클라이언트 사이드 검색 (경로/액션)
            if (filter.searchKeyword) {
                const keyword = filter.searchKeyword.toLowerCase();
                fetchedLogs = fetchedLogs.filter(log =>
                    (log.path && log.path.toLowerCase().includes(keyword)) ||
                    (log.action && log.action.toLowerCase().includes(keyword))
                );
            }

            setLogs(fetchedLogs);

        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // 헬퍼 함수들 (시간 포맷 등)
    const formatTime = (log) => {
        const timestamp = log.timestamp;
        if (!timestamp) return '-';
        try {
            return new Date(timestamp).toLocaleString('ko-KR');
        } catch (e) { return timestamp; }
    };

    const getStatusColor = (status) => {
        if (status >= 200 && status < 300) return 'bg-green-100 text-green-800';
        if (status >= 400) return 'bg-red-100 text-red-800';
        return 'bg-blue-100 text-blue-800';
    };

    return (
        <div className="min-h-screen bg-gray-100">
            <header className="bg-white shadow-sm border-b border-gray-200">
                <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
                    <div className="flex items-center space-x-4">
                        <Link to="/" className="text-gray-600 hover:text-gray-900">
                            <i className="fas fa-arrow-left"></i>
                        </Link>
                        <h1 className="text-xl font-bold text-gray-800">
                            <i className="fas fa-user-shield mr-2 text-purple-600"></i>
                            관리자 로그 센터
                        </h1>
                    </div>
                </div>
            </header>

            <div className="max-w-7xl mx-auto px-4 py-8">
                {/* 필터 패널 */}
                <div className="bg-white rounded-lg shadow p-6 mb-6">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                        {/* 기간 선택 */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">기간</label>
                            <select
                                value={filter.days}
                                onChange={(e) => setFilter({ ...filter, days: parseInt(e.target.value) })}
                                className="w-full border rounded-md p-2"
                            >
                                <option value="1">오늘</option>
                                <option value="7">최근 7일</option>
                                <option value="30">최근 30일</option>
                                <option value="0">전체</option>
                            </select>
                        </div>

                        {/* 사용자 검색 (추가됨) */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">사용자 ID</label>
                            <div className="flex">
                                <input
                                    type="text"
                                    placeholder="ID 입력 (엔터)"
                                    value={filter.targetUser}
                                    onChange={(e) => setFilter({ ...filter, targetUser: e.target.value })}
                                    onKeyPress={(e) => e.key === 'Enter' && fetchLogs()}
                                    className="w-full border rounded-l-md p-2"
                                />
                                <button onClick={fetchLogs} className="bg-purple-600 text-white px-3 rounded-r-md hover:bg-purple-700">
                                    <i className="fas fa-search"></i>
                                </button>
                            </div>
                        </div>

                        {/* 로그 레벨 */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">레벨</label>
                            <select
                                value={filter.logLevel}
                                onChange={(e) => setFilter({ ...filter, logLevel: e.target.value })}
                                className="w-full border rounded-md p-2"
                            >
                                <option value="">전체</option>
                                <option value="INFO">INFO</option>
                                <option value="WARNING">WARNING</option>
                                <option value="ERROR">ERROR</option>
                            </select>
                        </div>

                        {/* 키워드 검색 */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">내용 검색</label>
                            <input
                                type="text"
                                placeholder="경로, 액션명..."
                                value={filter.searchKeyword}
                                onChange={(e) => setFilter({ ...filter, searchKeyword: e.target.value })}
                                onKeyPress={(e) => e.key === 'Enter' && fetchLogs()}
                                className="w-full border rounded-md p-2"
                            />
                        </div>
                    </div>
                </div>

                {/* 로그 리스트 */}
                <div className="bg-white rounded-lg shadow overflow-hidden">
                    <div className="p-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
                        <h2 className="font-bold text-gray-700">전체 로그 ({logs.length}건)</h2>
                        <button onClick={fetchLogs} className="text-sm text-blue-600 hover:underline">
                            <i className="fas fa-sync-alt mr-1"></i>새로고침
                        </button>
                    </div>

                    {loading ? (
                        <div className="p-10 text-center text-gray-500">로딩 중...</div>
                    ) : error ? (
                        <div className="p-10 text-center text-red-500">
                            <i className="fas fa-exclamation-triangle mr-2"></i>{error}
                        </div>
                    ) : logs.length === 0 ? (
                        <div className="p-10 text-center text-gray-400">조회된 로그가 없습니다.</div>
                    ) : (
                        <div className="divide-y divide-gray-100">
                            {logs.map((log, idx) => (
                                <div key={idx} className="p-4 hover:bg-blue-50 transition duration-150">
                                    <div className="flex justify-between items-start mb-2">
                                        <div className="flex items-center gap-3">
                                            {/* 레벨 배지 */}
                                            <span className={`px-2 py-0.5 text-xs font-bold rounded ${
                                                log.level === 'ERROR' ? 'bg-red-100 text-red-700' :
                                                log.level === 'WARNING' ? 'bg-orange-100 text-orange-700' :
                                                'bg-blue-100 text-blue-700'
                                            }`}>
                                                {log.level || 'INFO'}
                                            </span>
                                            {/* 사용자 ID 표시 (관리자 뷰 핵심) */}
                                            <span className="flex items-center text-sm font-bold text-gray-800 bg-gray-100 px-2 py-0.5 rounded">
                                                <i className="fas fa-user mr-1 text-xs text-gray-500"></i>
                                                {log.user_id || log.LoginId || 'Anonymous'}
                                            </span>
                                            <span className="text-sm font-medium text-gray-600">
                                                {log.action}
                                            </span>
                                        </div>
                                        <span className="text-xs text-gray-400">{formatTime(log)}</span>
                                    </div>

                                    <div className="pl-2 border-l-2 border-gray-200 ml-1">
                                        <div className="text-sm text-gray-600 font-mono break-all bg-gray-50 p-2 rounded mb-1">
                                            {log.path}
                                        </div>
                                        <div className="flex gap-4 text-xs text-gray-500">
                                            <span>Method: <span className="font-semibold">{log.method}</span></span>
                                            <span>Status: <span className={`font-bold ${getStatusColor(log.status).split(' ')[1]}`}>{log.status}</span></span>
                                            {log.duration && <span>Duration: {log.duration}s</span>}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default AdminLogHistoryPage;