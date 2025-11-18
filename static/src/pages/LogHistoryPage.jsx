import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';

function LogHistoryPage() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [filter, setFilter] = useState({
        days: 7,
        logLevel: '',
        searchKeyword: ''
    });
    const [stats, setStats] = useState(null);
    const navigate = useNavigate();

    // 로그인 확인
    useEffect(() => {
        const token = localStorage.getItem('accessToken');
        if (!token) {
            navigate('/login');
            return;
        }
        
        fetchLogs();
        fetchStats();
    }, [filter.days, filter.logLevel]);

    // 로그 가져오기
    const fetchLogs = async () => {
        setLoading(true);
        setError(null);

        try {
            const token = localStorage.getItem('accessToken');
            const params = new URLSearchParams({
                days: filter.days,
                max_results: 100
            });

            if (filter.logLevel) {
                params.append('log_level', filter.logLevel);
            }

            const response = await fetch(`http://localhost:8000/api/v1/logs/my-activities?${params}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('로그 조회 실패');
            }

            const data = await response.json();

            // 🔍 디버깅: API 응답 확인
            console.log('=== API 응답 디버깅 ===');
            console.log('전체 응답:', data);
            if (data.logs && data.logs.length > 0) {
                console.log('첫 번째 로그:', data.logs[0]);
                console.log('필드명:', Object.keys(data.logs[0]));
            }

            setLogs(data.logs || []);
        } catch (err) {
            console.error('로그 조회 에러:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // 통계 가져오기
    const fetchStats = async () => {
        try {
            const token = localStorage.getItem('accessToken');
            const response = await fetch('http://localhost:8000/api/v1/logs/stats', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                setStats(data);
            }
        } catch (err) {
            console.error('통계 조회 실패:', err);
        }
    };

    // 검색
    const handleSearch = async () => {
        if (!filter.searchKeyword.trim()) {
            fetchLogs();
            return;
        }

        setLoading(true);
        try {
            const token = localStorage.getItem('accessToken');
            const params = new URLSearchParams({
                keyword: filter.searchKeyword,
                max_results: 100
            });

            if (filter.logLevel) {
                params.append('log_level', filter.logLevel);
            }

            const response = await fetch(`http://localhost:8000/api/v1/logs/search?${params}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('검색 실패');
            }

            const data = await response.json();
            setLogs(data.results || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // 로그 레벨 색상
    const getLogLevelColor = (level) => {
        const colors = {
            'DEBUG': 'bg-gray-100 text-gray-800',
            'INFO': 'bg-blue-100 text-blue-800',
            'WARNING': 'bg-yellow-100 text-yellow-800',
            'ERROR': 'bg-red-100 text-red-800',
            'CRITICAL': 'bg-purple-100 text-purple-800'
        };
        return colors[level] || 'bg-gray-100 text-gray-800';
    };

    // 🔧 한글/영문 필드명 호환 함수
    const getFieldValue = (log, englishField, koreanField) => {
        return log[englishField] || log[koreanField];
    };

    // 🔧 시간 포맷 (한글/영문 호환)
    const formatTime = (log) => {
        // 영문 필드명 우선, 한글 필드명 대체
        const timestamp = getFieldValue(log, 'timestamp', '타임스탬프');

        if (!timestamp) {
            console.warn('timestamp 없음:', log);
            return '시간 정보 없음';
        }

        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) {
                console.warn('날짜 파싱 실패:', timestamp);
                return timestamp; // 원본 그대로 표시
            }

            return date.toLocaleString('ko-KR', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch (e) {
            console.error('formatTime 에러:', e, timestamp);
            return timestamp || '날짜 오류';
        }
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
                            <h1 className="text-xl font-bold text-gray-900">활동 로그</h1>
                        </div>
                        <div className="flex items-center space-x-4">
                            <span className="text-sm text-gray-600">
                                {localStorage.getItem('UserName') || '사용자'} {/* UserName으로 변경 */}
                            </span>
                        </div>
                    </div>
                </div>
            </header>

            <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
                {/* 통계 카드 */}
                {stats && (
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                        <div className="bg-white rounded-lg shadow p-4">
                            <div className="text-sm text-gray-600">전체 로그</div>
                            <div className="text-2xl font-bold text-gray-900">{stats.total_logs || 0}</div>
                        </div>
                        <div className="bg-white rounded-lg shadow p-4">
                            <div className="text-sm text-gray-600">INFO</div>
                            <div className="text-2xl font-bold text-blue-600">
                                {stats.level_counts?.INFO || stats.log_level_counts?.INFO || 0}
                            </div>
                        </div>
                        <div className="bg-white rounded-lg shadow p-4">
                            <div className="text-sm text-gray-600">WARNING</div>
                            <div className="text-2xl font-bold text-yellow-600">
                                {stats.level_counts?.WARNING || stats.log_level_counts?.WARNING || 0}
                            </div>
                        </div>
                        <div className="bg-white rounded-lg shadow p-4">
                            <div className="text-sm text-gray-600">ERROR</div>
                            <div className="text-2xl font-bold text-red-600">
                                {stats.level_counts?.ERROR || stats.log_level_counts?.ERROR || 0}
                            </div>
                        </div>
                    </div>
                )}

                {/* 필터 */}
                <div className="bg-white rounded-lg shadow p-4 mb-6">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
                                <option value="DEBUG">DEBUG</option>
                                <option value="INFO">INFO</option>
                                <option value="WARNING">WARNING</option>
                                <option value="ERROR">ERROR</option>
                                <option value="CRITICAL">CRITICAL</option>
                            </select>
                        </div>

                        <div className="md:col-span-2">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                검색
                            </label>
                            <div className="flex space-x-2">
                                <input
                                    type="text"
                                    value={filter.searchKeyword}
                                    onChange={(e) => setFilter({ ...filter, searchKeyword: e.target.value })}
                                    placeholder="키워드로 검색..."
                                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                                />
                                <button
                                    onClick={handleSearch}
                                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    <i className="fas fa-search"></i>
                                </button>
                                {filter.searchKeyword && (
                                    <button
                                        onClick={() => {
                                            setFilter({ ...filter, searchKeyword: '' });
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
                            로그 목록 ({logs.length}개)
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
                            </div>
                        ) : logs.length === 0 ? (
                            <div className="p-8 text-center">
                                <i className="fas fa-inbox text-4xl text-gray-400 mb-2"></i>
                                <p className="text-gray-600">로그가 없습니다.</p>
                            </div>
                        ) : (
                            logs.map((log, index) => {
                                // 한글/영문 필드명 호환
                                const logLevel = getFieldValue(log, 'log_level', '로그레벨');
                                const message = getFieldValue(log, 'message', '메시지');
                                const service = getFieldValue(log, 'service', '서비스');
                                const logger = getFieldValue(log, 'logger', '로거');
                                const details = getFieldValue(log, 'details', '추가정보');

                                return (
                                    <div key={index} className="p-4 hover:bg-gray-50 transition">
                                        <div className="flex items-start justify-between">
                                            <div className="flex-1">
                                                <div className="flex items-center space-x-2 mb-2">
                                                    <span className={`px-2 py-1 text-xs font-semibold rounded ${getLogLevelColor(logLevel)}`}>
                                                        {logLevel}
                                                    </span>
                                                    {service && (
                                                        <span className="text-xs text-gray-500">
                                                            [{service}]
                                                        </span>
                                                    )}
                                                    {logger && (
                                                        <span className="text-xs text-gray-500">
                                                            {`{${logger}}`}
                                                        </span>
                                                    )}
                                                </div>
                                                <p className="text-sm text-gray-900 mb-1">{message}</p>
                                                {details && Object.keys(details).length > 0 && (
                                                    <details className="mt-2">
                                                        <summary className="text-xs text-blue-600 cursor-pointer hover:underline">
                                                            상세 정보 보기
                                                        </summary>
                                                        <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-x-auto">
                                                            {JSON.stringify(details, null, 2)}
                                                        </pre>
                                                    </details>
                                                )}
                                            </div>
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