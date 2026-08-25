import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App.jsx'
import './styles/global.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <ConfigProvider
        locale={zhCN}
        theme={{
          token: {
            colorPrimary: '#4f6ef7',
            colorInfo: '#4f6ef7',
            colorLink: '#4f6ef7',
            borderRadius: 10,
            colorBgContainer: '#ffffff',
            colorText: '#1f2430',
            colorTextSecondary: '#6b7280',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", sans-serif',
          },
          components: {
            Layout: {
              headerBg: 'transparent', // 实际颜色由 global.css 控制
              siderBg: '#f5f5f5',
            },
            Card: {
              borderRadiusLG: 16,
            },
            Table: {
              borderRadius: 12,
              headerBg: '#f7f8fc',
            },
            Menu: {
              itemBg: 'transparent',
            },
            Tabs: {
              inkBarColor: '#4f6ef7',
              itemSelectedColor: '#4f6ef7',
              itemHoverColor: '#4f6ef7',
            },
          }
        }}
      >
        <App />
      </ConfigProvider>
    </BrowserRouter>
  </React.StrictMode>,
)