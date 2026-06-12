import { Layout, Menu, Button, Avatar, Dropdown, Space } from 'antd'
import { UserOutlined, BookOutlined, LogoutOutlined, HistoryOutlined, SunOutlined, MoonOutlined } from '@ant-design/icons'
import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'

const { Header } = Layout

const Navbar = ({ isAuthenticated, user, logout }) => {
  const navigate = useNavigate()
  // 可选：主题切换状态，如果不需要可删除
  const [isDark, setIsDark] = useState(false)

  const menuItems = isAuthenticated ? [
    { key: 'courses', icon: <BookOutlined />, label: <Link to="/courses">我的课程</Link> },
    { key: 'submissions', icon: <HistoryOutlined />, label: <Link to="/submissions">提交记录</Link> },
  ] : []

  const userMenu = {
    items: [
      { key: 'profile', icon: <UserOutlined />, label: <Link to="/profile">个人中心</Link> },
      { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: logout },
    ],
  }

  return (
    <Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 1000 }}>
      <div className="logo" style={{ fontSize: '20px', fontWeight: 'bold', marginRight: 48 }}>
        <Link to="/" style={{ color: '#1677ff' }}>在线教学平台</Link>
      </div>
      {isAuthenticated ? (
        <>
          <Menu mode="horizontal" items={menuItems} style={{ flex: 1, minWidth: 0, borderBottom: 'none', background: 'transparent' }} />
          <Space>
            <Dropdown menu={userMenu} placement="bottomRight">
              <Space style={{ cursor: 'pointer' }}>
                <Avatar icon={<UserOutlined />} />
                <span>{user?.username}</span>
              </Space>
            </Dropdown>
          </Space>
        </>
      ) : (
        <Button type="primary" onClick={() => navigate('/login')} style={{ borderRadius: 20 }}>
          登录 / 注册
        </Button>
      )}
    </Header>
  )
}

export default Navbar