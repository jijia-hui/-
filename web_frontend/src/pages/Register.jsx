import { Form, Input, Button, Card, message, Checkbox, Space } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined, ReadOutlined, SafetyOutlined } from '@ant-design/icons'
import { Link, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import api from '../api/client'

const firstError = (data) => {
  if (!data) return ''
  if (typeof data.detail === 'string') return data.detail
  for (const key of ['verification_code', 'email', 'username', 'password']) {
    const val = data[key]
    if (Array.isArray(val) && val[0]) return val[0]
    if (typeof val === 'string') return val
  }
  return ''
}

const Register = () => {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [countdown, setCountdown] = useState(0)

  useEffect(() => {
    if (countdown <= 0) return undefined
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [countdown])

  const sendCode = async () => {
    try {
      await form.validateFields(['email'])
    } catch {
      return
    }
    const email = form.getFieldValue('email')
    setSending(true)
    try {
      await api.post('/auth/send-code/', { email })
      message.success('验证码已发送，请查收邮箱（含垃圾箱）')
      setCountdown(60)
    } catch (error) {
      const data = error.response?.data
      const wait = data?.retry_after
      if (error.response?.status === 429 && wait) {
        setCountdown(wait)
      }
      message.error(firstError(data) || '验证码发送失败')
    } finally {
      setSending(false)
    }
  }

  const onFinish = async (values) => {
    setLoading(true)
    try {
      await api.post('/users/', {
        username: values.username,
        password: values.password,
        email: values.email,
        verification_code: values.verification_code,
        is_teacher: !!values.is_teacher,
      })
      message.success('注册成功，请登录')
      navigate('/login')
    } catch (error) {
      message.error(firstError(error.response?.data) || '注册失败，请检查验证码或用户名')
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
          <p>验证邮箱后即可加入在线教学平台</p>
        </div>
        <Form form={form} onFinish={onFinish} size="large">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined style={{ color: '#9aa3b8' }} />} placeholder="用户名" />
          </Form.Item>
          <Form.Item name="email" rules={[
            { required: true, message: '请输入邮箱' },
            { type: 'email', message: '请输入有效邮箱' },
          ]}>
            <Input prefix={<MailOutlined style={{ color: '#9aa3b8' }} />} placeholder="邮箱" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 24 }}>
            <Space.Compact className="code-compact">
              <Form.Item
                name="verification_code"
                noStyle
                rules={[
                  { required: true, message: '请输入邮箱验证码' },
                  { len: 6, message: '验证码为 6 位数字' },
                ]}
              >
                <Input
                  prefix={<SafetyOutlined style={{ color: '#9aa3b8' }} />}
                  placeholder="6 位验证码"
                  maxLength={6}
                />
              </Form.Item>
              <Button
                type="primary"
                ghost
                onClick={sendCode}
                loading={sending}
                disabled={countdown > 0}
              >
                {countdown > 0 ? `${countdown}s 后重发` : '获取验证码'}
              </Button>
            </Space.Compact>
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
