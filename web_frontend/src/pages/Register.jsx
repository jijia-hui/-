import { Form, Input, Button, Card, message, Typography, Checkbox } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

const { Title } = Typography

const Register = () => {
  const navigate = useNavigate()

  const onFinish = async (values) => {
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
    }
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
      <Card style={{ width: 400 }}>
        <Title level={2} style={{ textAlign: 'center' }}>注册</Title>
        <Form onFinish={onFinish}>
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>
          <Form.Item name="email" rules={[{ type: 'email', message: '请输入有效邮箱' }]}>
            <Input prefix={<MailOutlined />} placeholder="邮箱" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item name="is_teacher" valuePropName="checked" initialValue={false}>
            <Checkbox>注册为教师</Checkbox>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>注册</Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default Register