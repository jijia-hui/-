import { Form, Input, Button, Card, message, Typography } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/client'

const { Title } = Typography

const Login = ({ onLogin }) => {
  const navigate = useNavigate()

  const onFinish = async (values) => {
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
    }
  };


  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
      <Card style={{ width: 400 }}>
        <Title level={2} style={{ textAlign: 'center' }}>登录</Title>
        <Form onFinish={onFinish}>
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>登录</Button>
          </Form.Item>
          <div style={{ textAlign: 'center' }}>
            还没有账号？ <Link to="/register">立即注册</Link>
          </div>
        </Form>
      </Card>
    </div>
  )
}

export default Login