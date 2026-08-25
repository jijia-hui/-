import { Form, Input, Button, Card, message, Checkbox } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined, ReadOutlined } from '@ant-design/icons'
import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import api from '../api/client'

const Register = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const onFinish = async (values) => {
    setLoading(true)
    try {
      // 调用后端注册 API（假设存在 /api/users/）
      await api.post('/users/', {
        username: values.username,
        password: values.password,
        email: values.email,
        is_teacher: !!values.is_teacher, // 确保是布尔值
      })
      message.success('注册成功，请登录')
      navigate('/login')
    } catch (error) {
      message.error('注册失败，用户名可能已存在')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <Card className="auth-card" bordered={false}>
        <div className="auth-brand">
          <span className="brand-icon-box">
            <ReadOutlined />
          </span>
          <h2>创建账号</h2>
          <p>加入在线教学平台，开启教与学的新体验</p>
        </div>
        <Form onFinish={onFinish} size="large">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined style={{ color: '#9aa3b8' }} />} placeholder="用户名" />
          </Form.Item>
          <Form.Item name="email" rules={[
            { required: true, message: '请输入邮箱' },
            { type: 'email', message: '请输入有效邮箱' },
          ]}>
            <Input prefix={<MailOutlined style={{ color: '#9aa3b8' }} />} placeholder="邮箱" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined style={{ color: '#9aa3b8' }} />} placeholder="密码" />
          </Form.Item>
          <Form.Item name="is_teacher" valuePropName="checked" initialValue={false} style={{ marginBottom: 16 }}>
            <Checkbox>注册为教师</Checkbox>
          </Form.Item>
          <Form.Item style={{ marginBottom: 16 }}>
            <Button type="primary" htmlType="submit" block loading={loading}>注 册</Button>
          </Form.Item>
          <div style={{ textAlign: 'center', color: '#6b7280' }}>
            已有账号？ <Link to="/login">返回登录</Link>
          </div>
        </Form>
      </Card>
    </div>
  )
}

export default Register
