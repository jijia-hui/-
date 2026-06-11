import { Card, Descriptions, Avatar, Button, message } from 'antd'
import { UserOutlined } from '@ant-design/icons'

const Profile = ({ user }) => {
  if (!user) return null
  return (
    <div style={{ padding: 24 }}>
      <Card title="个人信息">
        <Descriptions column={1}>
          <Descriptions.Item label="头像">
            <Avatar icon={<UserOutlined />} size={64} />
          </Descriptions.Item>
          <Descriptions.Item label="用户名">{user.username}</Descriptions.Item>
          <Descriptions.Item label="邮箱">{user.email || '未设置'}</Descriptions.Item>
          <Descriptions.Item label="身份">{user.is_teacher ? '教师' : '学生'}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  )
}

export default Profile