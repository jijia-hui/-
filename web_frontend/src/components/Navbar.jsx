import { Layout, Menu, Button, Avatar, Dropdown, Space, Tag } from 'antd'
import { UserOutlined, BookOutlined, LogoutOutlined, HistoryOutlined, ReadOutlined } from '@ant-design/icons'
import { Link, useNavigate, useLocation } from 'react-router-dom'

const { Header } = Layout

const Navbar = ({ isAuthenticated, user, logout }) => {
  const navigate = useNavigate()
  const location = useLocation()

  const selectedKey = location.pathname.startsWith('/submissions') ? 'submissions' : 'courses'

  const menuItems = isAuthenticated ? [
    { key: 'courses', icon: <BookOutlined />, label: <Link to="/courses">我的课程</Link> },
    { key: 'submissions', icon: <HistoryOutlined />, label: <Link to="/submissions">提交记录</Link> },
  ] : []

  const userMenu = {
    items: [
      { key: 'profile', icon: <UserOutlined />, label: <Link to="/profile">个人中心</Link> },
      { type: 'divider' },
      { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true, onClick: logout },
    ],
  }

  return (
    <Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 1000 }}>
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 12, marginRight: 40 }}>
        <span className="brand-icon-box" style={{ width: 36, height: 36, fontSize: 18, borderRadius: 10 }}>
          <ReadOutlined />
        </span>
        <span className="brand-gradient-text" style={{ fontSize: 19, fontWeight: 800, letterSpacing: 1 }}>
          在线教学平台
        </span>
      </Link>
      {isAuthenticated ? (
        <>
          <Menu
            mode="horizontal"
            items={menuItems}
            selectedKeys={[selectedKey]}
            style={{ flex: 1, minWidth: 0, borderBottom: 'none', background: 'transparent' }}
          />
          <Dropdown menu={userMenu} placement="bottomRight" arrow>
            <Space style={{ cursor: 'pointer', padding: '4px 8px', borderRadius: 12 }} className="navbar-user">
              <Avatar
                icon={<UserOutlined />}
                style={{ background: 'linear-gradient(135deg, #4f6ef7 0%, #22c1c3 100%)' }}
              />
              <span style={{ fontWeight: 500 }}>{user?.username}</span>
              <Tag color={user?.is_teacher ? 'geekblue' : 'cyan'} style={{ marginRight: 0 }}>
                {user?.is_teacher ? '教师' : '学生'}
              </Tag>
            </Space>
          </Dropdown>
        </>
      ) : (
        <Button type="primary" onClick={() => navigate('/login')} style={{ borderRadius: 20, padding: '0 24px' }}>
          登录 / 注册
        </Button>
      )}
    </Header>
  )
}

export default Navbar
