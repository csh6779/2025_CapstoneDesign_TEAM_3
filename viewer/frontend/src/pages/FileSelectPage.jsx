import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:9000';

function FileSelectPage() {
    const [uploads, setUploads] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedLocation, setSelectedLocation] = useState('f_drive');
    const [searchKeyword, setSearchKeyword] = useState('');
    const [selectedDatasets, setSelectedDatasets] = useState([]);

    const navigate = useNavigate();

    useEffect(() => {
        const token = localStorage.getItem('accessToken');
        if (!token) {
            navigate('/login');
            return;
        }

        fetchUploads();
    }, []);

    const fetchUploads = async () => {
        setLoading(true);
        setError(null);

        try {
            const token = localStorage.getItem('accessToken');

            // ✅ 크기 계산 안 함 (빠름)
            const response = await fetch(
                `${API_BASE_URL}/api/raw-uploads?calculate_size=false`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                }
            );

            if (!response.ok) {
                throw new Error('데이터셋 목록 조회 실패');
            }

            const data = await response.json();
            console.log('Precomputed 데이터셋:', data);
            setUploads(data.uploads || {});
        } catch (err) {
            console.error('데이터셋 조회 에러:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // ✅ 수정: 'c_drive' → 'converter'로 변경
    const getLocationName = (location) => {
        const names = {
            'f_drive': 'F 드라이브',
            'tmp': '임시 저장소',
            'converter': 'Converter'  // ✅ 수정됨
        };
        return names[location] || location;
    };

    // ✅ 데이터셋 정보 포맷팅
    const formatDatasetInfo = (dataset) => {
        if (!dataset.dimensions) return 'N/A';
        return `${dataset.dimensions.join(' × ')}`;
    };

    const formatTime = (isoString) => {
        if (!isoString) return '';
        const date = new Date(isoString);
        return date.toLocaleString('ko-KR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    // ✅ 데이터셋 선택/해제
    const toggleDatasetSelection = (dataset) => {
        const datasetId = `${dataset.location}-${dataset.name}`;
        if (selectedDatasets.some(d => `${d.location}-${d.name}` === datasetId)) {
            setSelectedDatasets(selectedDatasets.filter(d =>
                `${d.location}-${d.name}` !== datasetId
            ));
        } else {
            setSelectedDatasets([...selectedDatasets, dataset]);
        }
    };

    const isDatasetSelected = (dataset) => {
        const datasetId = `${dataset.location}-${dataset.name}`;
        return selectedDatasets.some(d => `${d.location}-${d.name}` === datasetId);
    };

    const handleLoadSelected = () => {
        if (selectedDatasets.length === 0) {
            alert('불러올 데이터셋을 선택해주세요.');
            return;
        }
        // TODO: 뷰어로 데이터셋 전달
        console.log('선택된 데이터셋:', selectedDatasets);
        navigate('/', { state: { selectedDatasets } });
    };

    const getFilteredDatasets = () => {
        const datasets = uploads[selectedLocation] || [];
        if (!searchKeyword.trim()) return datasets;

        const keyword = searchKeyword.toLowerCase();
        return datasets.filter(dataset =>
            dataset.name.toLowerCase().includes(keyword)
        );
    };

    const filteredDatasets = getFilteredDatasets();

    return (
        <div className="min-h-screen bg-gray-50">
            <header className="bg-white shadow-sm">
                <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                            <Link to="/" className="text-gray-600 hover:text-gray-900">
                                <i className="fas fa-arrow-left"></i>
                            </Link>
                            <h1 className="text-xl font-bold text-gray-900">데이터셋 선택</h1>
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
                        <div className="text-sm text-gray-600">전체 데이터셋</div>
                        <div className="text-2xl font-bold text-gray-900">
                            {Object.values(uploads).reduce((sum, datasets) => sum + datasets.length, 0)}
                        </div>
                    </div>
                    <div className="bg-white rounded-lg shadow p-4">
                        <div className="text-sm text-gray-600">선택됨</div>
                        <div className="text-2xl font-bold text-blue-600">
                            {selectedDatasets.length}
                        </div>
                    </div>
                    <div className="bg-white rounded-lg shadow p-4">
                        <div className="text-sm text-gray-600">F 드라이브</div>
                        <div className="text-2xl font-bold text-green-600">
                            {(uploads.f_drive || []).length}
                        </div>
                    </div>
                    {/* ✅ 수정: C 드라이브 → Converter */}
                    <div className="bg-white rounded-lg shadow p-4">
                        <div className="text-sm text-gray-600">Converter</div>
                        <div className="text-2xl font-bold text-purple-600">
                            {(uploads.converter || []).length}
                        </div>
                    </div>
                </div>

                {/* 필터 */}
                <div className="bg-white rounded-lg shadow p-4 mb-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                저장 위치
                            </label>
                            <select
                                value={selectedLocation}
                                onChange={(e) => setSelectedLocation(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                {Object.keys(uploads).map(location => (
                                    <option key={location} value={location}>
                                        {getLocationName(location)} ({(uploads[location] || []).length}개)
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="md:col-span-2">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                검색
                            </label>
                            <div className="flex space-x-2">
                                <input
                                    type="text"
                                    value={searchKeyword}
                                    onChange={(e) => setSearchKeyword(e.target.value)}
                                    placeholder="데이터셋명으로 검색..."
                                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                                <button
                                    onClick={() => setSearchKeyword('')}
                                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
                                >
                                    <i className="fas fa-times"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* 선택된 데이터셋 액션 */}
                {selectedDatasets.length > 0 && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <span className="font-medium text-blue-900">
                                    {selectedDatasets.length}개 데이터셋 선택됨
                                </span>
                            </div>
                            <div className="flex space-x-2">
                                <button
                                    onClick={() => setSelectedDatasets([])}
                                    className="px-4 py-2 bg-white text-gray-700 rounded-md hover:bg-gray-100 border"
                                >
                                    선택 해제
                                </button>
                                <button
                                    onClick={handleLoadSelected}
                                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                                >
                                    <i className="fas fa-eye mr-2"></i>
                                    뷰어로 불러오기
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* 데이터셋 목록 */}
                <div className="bg-white rounded-lg shadow">
                    <div className="p-4 border-b">
                        <h2 className="text-lg font-semibold text-gray-900">
                            {getLocationName(selectedLocation)} - {filteredDatasets.length}개
                        </h2>
                    </div>

                    <div className="divide-y">
                        {loading ? (
                            <div className="p-8 text-center">
                                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                                <p className="mt-2 text-gray-600">데이터셋 로딩 중...</p>
                            </div>
                        ) : error ? (
                            <div className="p-8 text-center">
                                <i className="fas fa-exclamation-circle text-4xl text-red-500 mb-2"></i>
                                <p className="text-red-600">{error}</p>
                                <button
                                    onClick={fetchUploads}
                                    className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md"
                                >
                                    다시 시도
                                </button>
                            </div>
                        ) : filteredDatasets.length === 0 ? (
                            <div className="p-8 text-center">
                                <i className="fas fa-folder-open text-4xl text-gray-400 mb-2"></i>
                                <p className="text-gray-600">변환된 데이터셋이 없습니다.</p>
                                <p className="text-sm text-gray-500 mt-2">
                                    Converter로 이미지를 변환해주세요.
                                </p>
                            </div>
                        ) : (
                            filteredDatasets.map((dataset, index) => (
                                <div
                                    key={index}
                                    className={`p-4 hover:bg-gray-50 cursor-pointer ${
                                        isDatasetSelected(dataset) ? 'bg-blue-50' : ''
                                    }`}
                                    onClick={() => toggleDatasetSelection(dataset)}
                                >
                                    <div className="flex items-start">
                                        <input
                                            type="checkbox"
                                            checked={isDatasetSelected(dataset)}
                                            onChange={() => {}}
                                            className="mt-1 h-4 w-4 text-blue-600"
                                        />
                                        <div className="ml-3 flex-1">
                                            <div className="flex justify-between">
                                                <div className="flex-1">
                                                    <h3 className="text-sm font-medium text-gray-900">
                                                        {dataset.name}
                                                    </h3>
                                                    <div className="mt-2 space-y-1">
                                                        <p className="text-xs text-gray-500">
                                                            <i className="fas fa-cube mr-1"></i>
                                                            크기: {formatDatasetInfo(dataset)}
                                                        </p>
                                                        <p className="text-xs text-gray-500">
                                                            <i className="fas fa-layer-group mr-1"></i>
                                                            타입: {dataset.type} ({dataset.data_type})
                                                        </p>
                                                        {dataset.chunk_sizes && (
                                                            <p className="text-xs text-gray-500">
                                                                <i className="fas fa-th mr-1"></i>
                                                                청크: {dataset.chunk_sizes.join(' × ')}
                                                            </p>
                                                        )}
                                                        {dataset.resolution && (
                                                            <p className="text-xs text-gray-500">
                                                                <i className="fas fa-ruler mr-1"></i>
                                                                해상도: {dataset.resolution.join(' × ')} nm
                                                            </p>
                                                        )}
                                                    </div>
                                                </div>
                                                <div className="text-right ml-4">
                                                    {dataset.size_gb > 0 && (
                                                        <div className="text-sm font-medium text-gray-900">
                                                            {dataset.size_gb} GB
                                                        </div>
                                                    )}
                                                    <div className="text-xs text-gray-500 mt-1">
                                                        {formatTime(dataset.modified_at)}
                                                    </div>
                                                    <div className="mt-2 flex items-center space-x-1">
                                                        {dataset.has_info && (
                                                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                                                <i className="fas fa-check-circle mr-1"></i>
                                                                Info
                                                            </span>
                                                        )}
                                                        {dataset.has_provenance && (
                                                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                                                <i className="fas fa-file-alt mr-1"></i>
                                                                Prov
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                            </div>
                        </div>
                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default FileSelectPage;