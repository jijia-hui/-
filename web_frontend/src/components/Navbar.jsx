import { Layout, Menu, Button, Avatar, Dropdown, Space } from 'antd'
import { UserOutlined, BookOutlined, LogoutOutlined, HistoryOutlined } from '@ant-design/icons'
import { Link, useNavigate } from 'react-router-dom'

const { Header } = Layout

const Navbar = ({ isAuthenticated, user, logout }) => {
  const navigate = useNavigate()

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
    <Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <div className="logo" style={{ color: 'white', fontSize: '20px', fontWeight: 'bold' }}>
        <Link to="/" style={{ color: 'white' }}>在线教学平台</Link>
      </div>
      {isAuthenticated ? (
        <>
          <Menu theme="dark" mode="horizontal" items={menuItems} style={{ flex: 1, minWidth: 0 }} />
          <Dropdown menu={userMenu} placement="bottomRight">
            <Space style={{ cursor: 'pointer' }}>
              <Avatar icon={<UserOutlined />} />
              <span style={{ color: 'white' }}>{user?.username}</span>
            </Space>
          </Dropdown>
        </>
      ) : (
        <Button type="primary" onClick={() => navigate('/login')}>登录 / 注册</Button>
      )}
    </Header>
  )
}

export default Navbar