import { Form, Input, Button, Card, message } from 'antd'
import { UserOutlined, LockOutlined, ReadOutlined } from '@ant-design/icons'
import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import api from '../api/client'

const Login = ({ onLogin }) => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const onFinish = async (values) => {
    setLoading(true)
    try {
      const res = await api.post('/auth/token/', {
        username: values.username,
        password: values.password,
      });
      const token = res.data.token;
      // 获取用户信息（需要额外接口，或者从 token 解码）
      const userRes = await api.get('/users/me/', {
        headers: { Authorization: `Token ${token}` }
      });
      onLogin(userRes.data, token);
      navigate('/courses');
      message.success('登录成功');
    } catch (error) {
      message.error('用户名或密码错误');
    } finally {
      setLoading(false)
    }
  };


  return (
    <div className="auth-page">
      <Card className="auth-card" bordered={false}>
        <div className="auth-brand">
          <span className="brand-icon-box">
            <ReadOutlined />
          </span>
          <h2>欢迎回来</h2>
          <p>登录在线教学平台，继续你的学习之旅</p>
        </div>
        <Form onFinish={onFinish} size="large">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined style={{ color: '#9aa3b8' }} />} placeholder="用户名" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined style={{ color: '#9aa3b8' }} />} placeholder="密码" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 16 }}>
            <Button type="primary" htmlType="submit" block loading={loading}>登 录</Button>
          </Form.Item>
          <div style={{ textAlign: 'center', color: '#6b7280' }}>
            还没有账号？ <Link to="/register">立即注册</Link>
          </div>
        </Form>
      </Card>
    </div>
  )
}

export default Login
