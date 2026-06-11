import { useEffect, useState } from 'react'
import { Card, Row, Col, Button, Spin, message, Tag, Modal, Form, Input } from 'antd'
import { PlusOutlined, UserAddOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

const CourseList = ({ user }) => {
  const [courses, setCourses] = useState([])
  const [loading, setLoading] = useState(true)
  const [createModal, setCreateModal] = useState(false)
  const [form] = Form.useForm()
  const navigate = useNavigate()

  const fetchCourses = async () => {
    try {
      const res = await api.get('/courses/')
      setCourses(res.data.results || res.data)
    } catch (error) {
      message.error('加载课程失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCourses()
  }, [])

  const handleCreate = async (values) => {
    try {
      await api.post('/courses/', values)
      message.success('课程创建成功')
      setCreateModal(false)
      form.resetFields()
      fetchCourses()
    } catch (error) {
      message.error('创建失败')
    }
  }

  const handleEnroll = async (courseId) => {
    try {
      await api.post(`/courses/${courseId}/enroll/`)
      message.success('选课成功')
      fetchCourses()
    } catch (error) {
      message.error('选课失败')
    }
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h1>我的课程</h1>
        {user?.is_teacher && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModal(true)}>
            创建课程
          </Button>
        )}
      </div>
      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          {courses.map(course => (
            <Col xs={24} sm={12} md={8} lg={6} key={course.id}>
              <Card
                title={course.name}
                extra={<Tag color={course.teacher_name === user?.username ? 'blue' : 'green'}>
                  {course.teacher_name === user?.username ? '我教的' : '我选的'}
                </Tag>}
                actions={[
                  <Button type="link" onClick={() => navigate(`/courses/${course.id}`)}>查看详情</Button>,
                  !user?.is_teacher && !course.students?.includes(user?.id) && (
                    <Button type="link" icon={<UserAddOutlined />} onClick={() => handleEnroll(course.id)}>选课</Button>
                  )
                ]}
              >
                <p>课程编号：{course.code}</p>
                <p>教师：{course.teacher_name}</p>
                <p>学生数：{course.student_count}</p>
              </Card>
            </Col>
          ))}
        </Row>
      </Spin>

      <Modal
        title="创建课程"
        open={createModal}
        onCancel={() => setCreateModal(false)}
        footer={null}
      >
        <Form form={form} onFinish={handleCreate} layout="vertical">
          <Form.Item name="name" label="课程名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="code" label="课程编号" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="课程描述">
            <Input.TextArea />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>创建</Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default CourseList