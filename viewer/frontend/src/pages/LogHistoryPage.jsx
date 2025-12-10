import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:9000';

function LogHistoryPage() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // ✅ 필터 상태 (기본값 설정)
    const [filter, setFilter] = useState({
        days: 7,
        logLevel: '',
        searchKeyword: ''
    });

    const navigate = useNavigate();

    // 로그인 확인 및 초기 로드
    useEffect(() => {
        const token = localStorage.getItem('accessToken');
        if (!token) {
            navigate('/login');
            return;
        }
        fetchLogs();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filter.days, filter.logLevel]); // 필터 변경 시 자동 재조회

    // 로그 가져오기 함수 (수정됨)
    const fetchLogs = async () => {
        setLoading(true);
        setError(null);

        try {
            const token = localStorage.getItem('accessToken');

            // 날짜 계산
            const endDate = new Date();
            const startDate = new Date();
            if (filter.days > 0) {
                startDate.setDate(endDate.getDate() - filter.days);
            } else {
                // 전체 조회 시 아주 옛날 날짜로 설정 (예: 2020년)
                startDate.setFullYear(2020);
            }

            // ✅ API 요청 파라미터 구성
            const params = new URLSearchParams({
                skip: 0,
                limit: 100,
                start_date: startDate.toISOString().split('T')[0],
                end_date: endDate.toISOString().split('T')[0]
            });

            if (filter.logLevel) {
                params.append('level', filter.logLevel);
            }

            const response = await fetch(`${API_BASE_URL}/api/v1/image-logs/me?${params}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '로그 조회 실패');
            }

            const data = await response.json();

            // 데이터 구조 처리
            let fetchedLogs = [];
            if (Array.isArray(data)) {
                fetchedLogs = data;
            } else if (data.logs && Array.isArray(data.logs)) {
                fetchedLogs = data.logs;
            }

            // 검색어 필터링 (클라이언트 사이드)
            if (filter.searchKeyword) {
                const keyword = filter.searchKeyword.toLowerCase();
                fetchedLogs = fetchedLogs.filter(log =>
                    (log.path && log.path.toLowerCase().includes(keyword)) ||
                    (log.action && log.action.toLowerCase().includes(keyword))
                );
            }

            setLogs(fetchedLogs);

        } catch (err) {
            console.error('로그 가져오기 에러:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // 검색 핸들러
    const handleSearch = () => {
        fetchLogs();
    };

    // 상태 색상 (백엔드 status 코드 기준)
    const getStatusColor = (status) => {
        if (status >= 200 && status < 300) return 'bg-green-100 text-green-800';
        if (status >= 400) return 'bg-red-100 text-red-800';
        return 'bg-blue-100 text-blue-800'; // 기타
    };

    // 시간 포맷
    const formatTime = (log) => {
        // 백엔드 키: timestamp
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

    // 파일 크기 포맷 (Duration으로 대체하거나 없으면 빈값)
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
                            {logs.filter(l => l.status >= 200 && l.status < 300).length}
                        </div>
                    </div>
                    <div className="bg-white rounded-lg shadow p-4">
                        <div className="text-sm text-gray-600">실패 (4xx/5xx)</div>
                        <div className="text-2xl font-bold text-red-600">
                            {logs.filter(l => l.status >= 400).length}
                        </div>
                    </div>
                    <div className="bg-white rounded-lg shadow p-4">
                        <div className="text-sm text-gray-600">기타</div>
                        <div className="text-2xl font-bold text-blue-600">
                            {logs.filter(l => l.status < 200 || (l.status >= 300 && l.status < 400)).length}
                        </div>
                    </div>
                </div>

                {/* 필터 */}
                <div className="bg-white rounded-lg shadow p-4 mb-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                기간
                            </label>
                            <select
                                value={filter.days}
                                onChange={(e) => setFilter({ ...filter, days: parseInt(e.target.value) })}
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
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                로그 레벨
                            </label>
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
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                검색
                            </label>
                            <div className="flex space-x-2">
                                <input
                                    type="text"
                                    value={filter.searchKeyword}
                                    onChange={(e) => setFilter({ ...filter, searchKeyword: e.target.value })}
                                    placeholder="경로 또는 액션 검색..."
                                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                                />
                                <button
                                    onClick={handleSearch}
                                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                                >
                                    <i className="fas fa-search"></i>
                                </button>
                                {filter.searchKeyword && (
                                    <button
                                        onClick={() => {
                                            setFilter({ ...filter, searchKeyword: '' });
                                            // 검색어 초기화 시 전체 목록 다시 로드는 useEffect에 의해 처리됨 (필요시 별도 호출)
                                            fetchLogs();
                                        }}
                                        className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
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
                                // ✅ 백엔드 키에 맞춰 변수 할당
                                const status = log.status || 0;
                                const actionName = log.action || 'Unknown';
                                const path = log.path || '';
                                const duration = log.duration;

                                return (
                                    <div key={index} className="p-4 hover:bg-gray-50 transition">
                                        <div className="flex items-start justify-between">
                                            <div className="flex-1">
                                                <div className="flex items-center space-x-2 mb-2">
                                                    {/* 상태 배지 */}
                                                    <span className={`px-2 py-1 text-xs font-semibold rounded ${getStatusColor(status)}`}>
                                                        {status === 200 ? 'SUCCESS' : status}
                                                    </span>
                                                    {/* 액션 이름 */}
                                                    <span className="text-sm font-medium text-gray-900">
                                                        {actionName}
                                                    </span>
                                                </div>

                                                {/* 경로 표시 */}
                                                <div className="text-sm text-gray-600 break-all mb-1">
                                                    <span className="font-semibold mr-1">Path:</span>
                                                    {path}
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
                                                        {log.method}
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