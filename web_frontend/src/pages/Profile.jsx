import { Card, Descriptions, Avatar } from 'antd'
import { UserOutlined, MailOutlined, IdcardOutlined } from '@ant-design/icons'

const Profile = ({ user }) => {
  if (!user) return null
  return (
    <div className="page-container" style={{ maxWidth: 860 }}>
      <div className="profile-hero">
        <Avatar
          size={80}
          icon={<UserOutlined />}
          style={{ background: 'rgba(255,255,255,0.25)', flexShrink: 0 }}
        />
        <div>
          <h2>{user.username}</h2>
          <div className="hero-sub">
            <span className="profile-role-tag">{user.is_teacher ? '教师' : '学生'}</span>
            <span><MailOutlined /> {user.email || '未设置邮箱'}</span>
          </div>
        </div>
      </div>
      <Card title="账号信息" bordered={false}>
        <Descriptions column={1} bordered size="middle">
          <Descriptions.Item label={<span><IdcardOutlined /> 用户名</span>}>{user.username}</Descriptions.Item>
          <Descriptions.Item label={<span><MailOutlined /> 邮箱</span>}>{user.email || '未设置'}</Descriptions.Item>
          <Descriptions.Item label={<span><UserOutlined /> 身份</span>}>
            {user.is_teacher ? '教师（可创建课程、发布与批改作业）' : '学生（可选课、提交作业）'}
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  )
}

export default Profile
