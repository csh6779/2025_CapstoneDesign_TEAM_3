// API 서비스 - 백엔드 통신
import axios from 'axios';

// Docker 환경에서는 backend 서비스명 사용, 로컬에서는 localhost
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:9000';

// Axios 인스턴스 생성
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터 - JWT 토큰 자동 추가
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터 - 토큰 만료 처리
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 토큰 만료 또는 인증 실패
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 인증 관련 API
export const authAPI = {
  // 회원가입
  register: async (userData) => {
    const response = await api.post('/api/v1/auth/register', userData);
    return response.data;
  },

  // 로그인
  login: async (credentials) => {
    const response = await api.post('/api/v1/auth/login', credentials);
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
    }
    return response.data;
  },

  // 로그아웃
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  },

  // 현재 사용자 정보
  getCurrentUser: async () => {
    const response = await api.get('/api/v1/auth/me');
    return response.data;
  },

  // 로컬 스토리지에서 사용자 정보 가져오기
  getStoredUser: () => {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },

  // 인증 상태 확인
  isAuthenticated: () => {
    return !!localStorage.getItem('access_token');
  },
};

export const rawUploadAPI = {
  // 모든 위치의 원본 파일 조회
  getAll: async () => {
    const response = await api.get('/api/raw-uploads');
    return response.data;
  },

  // 특정 위치의 원본 파일 조회
  getByLocation: async (location) => {
    const response = await api.get(`/api/raw-uploads/${location}`);
    return response.data;
  },

  // 파일 상세 정보
  getFileInfo: async (location, filePath) => {
    const response = await api.get(`/api/raw-uploads/${location}/file-info`, {
      params: { file_path: filePath }
    });
    return response.data;
  },
};

// 북마크 관련 API
export const bookmarkAPI = {
  // 북마크 생성
  create: async (bookmarkData) => {
    const response = await api.post('/api/v1/bookmarks', bookmarkData);
    return response.data;
  },

  // 북마크 목록 조회
  getAll: async () => {
    const response = await api.get('/api/v1/bookmarks');
    return response.data || [];
  },

  // 북마크 단일 조회
  getById: async (bookmarkId) => {
    const response = await api.get(`/api/v1/bookmarks/${bookmarkId}`);
    return response.data;
  },

  // 북마크 업데이트
  update: async (bookmarkId, bookmarkData) => {
    const response = await api.put(`/api/v1/bookmarks/${bookmarkId}`, bookmarkData);
    return response.data;
  },

  // 북마크 삭제
  delete: async (bookmarkId) => {
    const response = await api.delete(`/api/v1/bookmarks/${bookmarkId}`);
    return response.data;
  },
};

// 데이터셋 관련 API
export const datasetAPI = {
  // 모든 데이터셋 조회
  getAll: async () => {
    const response = await api.get('/api/datasets');
    return response.data;
  },

  // 특정 위치의 데이터셋 조회
  getByLocation: async (location) => {
    const response = await api.get(`/api/datasets/${location}`);
    return response.data;
  },

  // 데이터셋 정보 조회
  getInfo: async (location, datasetName) => {
    const response = await api.get(`/api/datasets/${location}/${datasetName}/info`);
    return response.data;
  },
};

// Health Check
export const healthCheck = async () => {
  const response = await api.get('/api/health');
  return response.data;
};

export default api;
