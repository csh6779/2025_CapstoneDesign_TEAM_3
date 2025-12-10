import React from 'react';
import ReactDOM from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import './index.css';

// 페이지 컴포넌트 불러오기
import MainPage from './pages/MainPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import FindPasswordPage from './pages/FindPasswordPage';
import LogHistoryPage from './pages/LogHistoryPage';
import FileSelectPage from './pages/FileSelectPage';
import Adminpage_static from './pages/Adminpage_static';
//import AdminPage from './pages/AdminPage';
//import AdminFileSelectPage from './pages/AdminFileSelectPage';

// ✅ [추가 1] 새로 만든 관리자 로그 페이지 불러오기
import AdminLogHistoryPage from './pages/AdminLogHistoryPage';

// 페이지 경로(URL)와 컴포넌트를 1:1로 매칭
const router = createBrowserRouter([
  {
    path: "/",
    element: <MainPage />,
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/signup",
    element: <SignupPage />,
  },
  {
    path: "/find-password",
    element: <FindPasswordPage />,
  },
  {
    path: "/log-history",
    element: <LogHistoryPage />,
  },
  {
    path: "/file-select",
    element: <FileSelectPage />,
  },
//  {
//    path: "/admin",
//    element: <AdminPage />,
//  },
//  {
//    path: "/admin/file-select",
//    element: <AdminFileSelectPage />,
//  },
//  // ✅ [추가 2] 관리자 로그 페이지 경로 등록
//  {
//    path: "/admin/logs",
//    element: <AdminLogHistoryPage />,
//  },
  {
    path: "/admin",
    element: <Adminpage_static />,
  },
]);

// React 앱을 실행
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);