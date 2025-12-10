// React 컴포넌트: Neuroglancer 뷰어 통합
// E:\GithubRepository\Projects\ati_lab_2025\viewer\frontend\src\components\NeuroglancerViewer.jsx

import React, { useState, useEffect } from 'react';
import axios from 'axios';

const NeuroglancerViewer = ({ location, datasetName, onClose }) => {
  const [neuroglancerUrl, setNeuroglancerUrl] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('iframe'); // 'iframe' or 'window'

  useEffect(() => {
    if (location && datasetName) {
      fetchNeuroglancerUrl();
    }
  }, [location, datasetName]);

  const fetchNeuroglancerUrl = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const token = localStorage.getItem('accessToken');
      const response = await axios.get(
        `http://localhost:9000/api/neuroglancer/state`,
        {
          params: {
            volume_name: datasetName,
            location: location
          },
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      // 로컬 Neuroglancer 서버 URL 사용
      const localUrl = response.data.url.replace(
        'http://neuroglancer:8080',
        'http://localhost:8080'
      );
      setNeuroglancerUrl(localUrl);
      
      console.log('✅ Neuroglancer URL:', localUrl);
      console.log('📊 Dataset Info:', response.data.volume_info);
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch Neuroglancer URL:', err);
      setError(err.response?.data?.detail || '데이터를 불러올 수 없습니다.');
      setLoading(false);
    }
  };

  const openInNewWindow = () => {
    if (neuroglancerUrl) {
      window.open(neuroglancerUrl, '_blank', 'width=1200,height=800');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Neuroglancer URL 생성 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-red-800 font-semibold mb-2">오류 발생</h3>
        <p className="text-red-600">{error}</p>
        <button
          onClick={fetchNeuroglancerUrl}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          다시 시도
        </button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* 컨트롤 바 */}
      <div className="bg-gray-100 p-4 flex items-center justify-between border-b">
        <div className="flex items-center space-x-4">
          <h3 className="font-semibold text-gray-800">
            🧠 {datasetName}
          </h3>
          <span className="text-sm text-gray-600">
            위치: {location}
          </span>
        </div>
        
        <div className="flex items-center space-x-2">
          {/* 보기 모드 선택 */}
          <div className="flex space-x-2">
            <button
              onClick={() => setViewMode('iframe')}
              className={`px-3 py-1 rounded text-sm ${
                viewMode === 'iframe'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              페이지 내
            </button>
            <button
              onClick={() => {
                setViewMode('window');
                openInNewWindow();
              }}
              className={`px-3 py-1 rounded text-sm ${
                viewMode === 'window'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              새 창
            </button>
          </div>

          {/* URL 복사 */}
          <button
            onClick={() => {
              navigator.clipboard.writeText(neuroglancerUrl);
              alert('URL이 클립보드에 복사되었습니다!');
            }}
            className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
          >
            📋 URL 복사
          </button>

          {/* 새로고침 */}
          <button
            onClick={fetchNeuroglancerUrl}
            className="px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700"
          >
            🔄 새로고침
          </button>

          {/* 닫기 */}
          {onClose && (
            <button
              onClick={onClose}
              className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
            >
              ✕ 닫기
            </button>
          )}
        </div>
      </div>

      {/* Neuroglancer iframe */}
      {viewMode === 'iframe' && (
        <iframe
          src={neuroglancerUrl}
          className="w-full flex-1 border-0"
          title="Neuroglancer Viewer"
          style={{ minHeight: '700px' }}
          allow="cross-origin-isolated"
        />
      )}

      {/* 새 창 모드 안내 */}
      {viewMode === 'window' && (
        <div className="flex-1 flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <div className="text-6xl mb-4">🪟</div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">
              새 창에서 열림
            </h3>
            <p className="text-gray-600 mb-4">
              Neuroglancer가 새 창에서 실행되고 있습니다.
            </p>
            <button
              onClick={openInNewWindow}
              className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              다시 열기
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default NeuroglancerViewer;
