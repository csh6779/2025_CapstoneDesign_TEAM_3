import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:9000';

// ✅ 로컬 날짜(YYYY-MM-DD) 생성: toISOString() UTC 밀림 방지
const toLocalDateString = (d) => {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
};

function LogHistoryPage() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // ✅ 필터 상태
    const [filter, setFilter] = useState({
        days: 7,
        logLevel: '',
        searchKeyword: ''
    });

    const navigate = useNavigate();

    // ✅ 로그 가져오기 함수
    const fetchLogs = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const token = localStorage.getItem('accessToken');
            if (!token) {
                navigate('/login');
                return;
            }

            // 날짜 계산 (로컬 기준)
            const endDate = new Date();
            const startDate = new Date();
            if (filter.days > 0) {
                startDate.setDate(endDate.getDate() - filter.days);
            } else {
                startDate.setFullYear(2020); // 전체 조회
            }

            // ✅ API 요청 파라미터 구성 (로컬 날짜)
            const params = new URLSearchParams({
                skip: '0',
                limit: '100',
                start_date: toLocalDateString(startDate),
                end_date: toLocalDateString(endDate),
            });

            if (filter.logLevel) {
                params.append('level', filter.logLevel);
            }

            const url = `${API_BASE_URL}/api/v1/image-logs/me?${params.toString()}`;

            const response = await fetch(url, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                // ✅ 401/403 등에서 json 파싱 실패 대비
                let msg = '로그 조회 실패';
                try {
                    const errorData = await response.json();
                    msg = errorData.detail || msg;
                } catch (_) { /* ignore */ }
                throw new Error(msg);
            }

            const data = await response.json();

            // ✅ 응답 형태 방어적으로 처리
            let fetchedLogs = [];
            if (Array.isArray(data)) fetchedLogs = data;
            else if (Array.isArray(data.logs)) fetchedLogs = data.logs;
            else if (Array.isArray(data.items)) fetchedLogs = data.items;
            else if (Array.isArray(data.data)) fetchedLogs = data.data;

            // ✅ 검색어 필터링: path/action/message 모두 검색
            if (filter.searchKeyword) {
                const keyword = filter.searchKeyword.toLowerCase();
                fetchedLogs = fetchedLogs.filter(log =>
                    (log.path && String(log.path).toLowerCase().includes(keyword)) ||
                    (log.action && String(log.action).toLowerCase().includes(keyword)) ||
                    (log.message && String(log.message).toLowerCase().includes(keyword))
                );
            }

            fetchedLogs = fetchedLogs.filter(log =>
                log.action || log.path || log.status !== undefined || log.method
            );
            
            // ✅ 디버그(원하면 지워도 됨)
            console.log('[LogHistory] request url:', url);
            console.log('[LogHistory] raw response:', data);
            console.log('[LogHistory] parsed logs length:', fetchedLogs.length);

            setLogs(fetchedLogs);

        } catch (err) {
            console.error('로그 가져오기 에러:', err);
            setError(err?.message || '로그 가져오기 실패');
            setLogs([]);
        } finally {
            setLoading(false);
        }
    }, [filter.days, filter.logLevel, filter.searchKeyword, navigate]);

    // 로그인 확인 + 필터 변경 시 자동 재조회
    useEffect(() => {
        fetchLogs();
    }, [fetchLogs]);

    // 검색 핸들러
    const handleSearch = () => {
        fetchLogs();
    };

    // 상태 색상
    const getStatusColor = (status) => {
        if (status >= 200 && status < 300) return 'bg-green-100 text-green-800';
        if (status >= 400) return 'bg-red-100 text-red-800';
        return 'bg-blue-100 text-blue-800';
    };

    // 시간 포맷
    const formatTime = (log) => {
        const timestamp = log.timestamp;
        if (!timestamp) return '시간 정보 없음';

        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) return timestamp;

            return date.toLocaleString('ko-KR', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch (e) {
            return timestamp;
        }
    };

    const formatDuration = (duration) => {
        if (!duration) return null;
        return `${duration}s`;
    };

    return (
        <div className="min-h-screen bg-gray-50">
            {/* 헤더 */}
            <header className="bg-white shadow-sm">
                <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                            <Link to="/" className="text-gray-600 hover:text-gray-900">
                                <i className="fas fa-arrow-left"></i>
                            </Link>
                            <h1 className="text-xl font-bold text-gray-900">이미지 처리 로그</h1>
                        </div>
                        <div className="flex items-center space-x-4">
                            <span className="text-sm text-gray-600">
                                {localStorage.getItem('UserName') || '사용자'}
                            </span>
                        </div>
                    </div>
                </div>
            </header>

            <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
                {/* 통계 카드 */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <div className="bg-white rounded-lg shadow p-4">
                        <div className="text-sm text-gray-600">전체 로그</div>
                        <div className="text-2xl font-bold text-gray-900">{logs.length}</div>
                    </div>
                    <div className="bg-white rounded-lg shadow p-4">
                        <div className="text-sm text-gray-600">성공 (200)</div>
                        <div className="text-2xl font-bold text-green-600">
                            {logs.filter(l => (l.status ?? 0) >= 200 && (l.status ?? 0) < 300).length}
                        </div>
                    </div>
                    <div className="bg-white rounded-lg shadow p-4">
                        <div className="text-sm text-gray-600">실패 (4xx/5xx)</div>
                        <div className="text-2xl font-bold text-red-600">
                            {logs.filter(l => (l.status ?? 0) >= 400).length}
                        </div>
                    </div>
                    <div className="bg-white rounded-lg shadow p-4">
                        <div className="text-sm text-gray-600">기타</div>
                        <div className="text-2xl font-bold text-blue-600">
                            {logs.filter(l => (l.status ?? 0) < 200 || ((l.status ?? 0) >= 300 && (l.status ?? 0) < 400)).length}
                        </div>
                    </div>
                </div>

                {/* 필터 */}
                <div className="bg-white rounded-lg shadow p-4 mb-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">기간</label>
                            <select
                                value={filter.days}
                                onChange={(e) => setFilter({ ...filter, days: parseInt(e.target.value, 10) })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="1">오늘</option>
                                <option value="7">최근 7일</option>
                                <option value="14">최근 14일</option>
                                <option value="30">최근 30일</option>
                                <option value="0">전체</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">로그 레벨</label>
                            <select
                                value={filter.logLevel}
                                onChange={(e) => setFilter({ ...filter, logLevel: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="">전체</option>
                                <option value="INFO">INFO</option>
                                <option value="WARNING">WARNING</option>
                                <option value="ERROR">ERROR</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">검색</label>
                            <div className="flex space-x-2">
                                <input
                                    type="text"
                                    value={filter.searchKeyword}
                                    onChange={(e) => setFilter({ ...filter, searchKeyword: e.target.value })}
                                    placeholder="경로/액션/메시지 검색..."
                                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                                />
                                <button
                                    onClick={handleSearch}
                                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                                >
                                    <i className="fas fa-search"></i>
                                </button>
                                {filter.searchKeyword && (
                                    <button
                                        onClick={() => setFilter({ ...filter, searchKeyword: '' })}
                                        className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
                                        title="검색어 지우기"
                                    >
                                        <i className="fas fa-times"></i>
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                {/* 로그 목록 */}
                <div className="bg-white rounded-lg shadow">
                    <div className="p-4 border-b border-gray-200">
                        <h2 className="text-lg font-semibold text-gray-900">
                            처리 로그 ({logs.length}개)
                        </h2>
                    </div>

                    <div className="divide-y divide-gray-200">
                        {loading ? (
                            <div className="p-8 text-center">
                                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                                <p className="mt-2 text-gray-600">로그를 불러오는 중...</p>
                            </div>
                        ) : error ? (
                            <div className="p-8 text-center">
                                <i className="fas fa-exclamation-circle text-4xl text-red-500 mb-2"></i>
                                <p className="text-red-600">{error}</p>
                                <button
                                    onClick={fetchLogs}
                                    className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                                >
                                    다시 시도
                                </button>
                            </div>
                        ) : logs.length === 0 ? (
                            <div className="p-8 text-center">
                                <i className="fas fa-inbox text-4xl text-gray-400 mb-2"></i>
                                <p className="text-gray-600">처리 로그가 없습니다.</p>
                            </div>
                        ) : (
                            logs.map((log, index) => {
                                // status가 없을 수도 있으니 null/undefined 구분
                                const hasStatus = log.status !== undefined && log.status !== null;
                                const status = hasStatus ? log.status : null;

                                // action이 없으면 message 기반으로 MESSAGE 표시
                                const actionName = log.action || (log.message ? 'MESSAGE' : 'Unknown');

                                const path = log.path || '';
                                const duration = log.duration;
                                const method = log.method || 'N/A';
                                const level = (log.level || '').toUpperCase(); // INFO/WARNING/ERROR
                                const userLabel = log.user || log.user_id || log.LoginId || log.login_id || 'N/A';

                                // ✅ status 없으면 level로 뱃지 보여주기
                                const getBadgeClass = () => {
                                    if (hasStatus) return getStatusColor(status);

                                    // status 없는 경우: level 기반 컬러
                                    if (level === 'ERROR') return 'bg-red-100 text-red-800';
                                    if (level === 'WARNING') return 'bg-yellow-100 text-yellow-800';
                                    return 'bg-blue-100 text-blue-800'; // INFO/기타
                                };

                                const badgeText = hasStatus
                                    ? (status === 200 ? 'SUCCESS' : status)
                                    : (level || 'INFO');

                                return (
                                    <div key={index} className="p-4 hover:bg-gray-50 transition">
                                        <div className="flex items-start justify-between">
                                            <div className="flex-1">
                                                <div className="flex items-center space-x-2 mb-2">
                                                    {/* 상태/레벨 배지 */}
                                                    <span className={`px-2 py-1 text-xs font-semibold rounded ${getBadgeClass()}`}>
                                                        {badgeText}
                                                    </span>

                                                    {/* 액션 이름 */}
                                                    <span className="text-sm font-medium text-gray-900">
                                                        {actionName}
                                                    </span>

                                                    {/* message가 있으면 옆에 표시 */}
                                                    {log.message && (
                                                        <span className="text-xs text-gray-500">
                                                            - {String(log.message)}
                                                        </span>
                                                    )}
                                                </div>

                                                {/* 경로 표시 */}
                                                <div className="text-sm text-gray-600 break-all mb-1">
                                                    <span className="font-semibold mr-1">Path:</span>
                                                    {path ? path : '(no path)'}
                                                </div>

                                                <div className="flex items-center space-x-4 text-xs text-gray-500">
                                                    {/* 소요 시간 */}
                                                    {duration && (
                                                        <span>
                                                            <i className="fas fa-clock mr-1"></i>
                                                            {formatDuration(duration)}
                                                        </span>
                                                    )}

                                                    {/* 메서드 */}
                                                    <span>
                                                        <i className="fas fa-globe mr-1"></i>
                                                        {method}
                                                    </span>

                                                    {/* 유저 */}
                                                    <span>
                                                        <i className="fas fa-user mr-1"></i>
                                                        {userLabel}
                                                    </span>
                                                </div>
                                            </div>

                                            {/* 시간 */}
                                            <div className="text-xs text-gray-500 ml-4 whitespace-nowrap">
                                                {formatTime(log)}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default LogHistoryPage;
