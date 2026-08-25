import { useEffect, useState } from 'react'
import { Card, Row, Col, Button, Spin, message, Tag, Modal, Form, Input, Empty } from 'antd'
import { PlusOutlined, UserAddOutlined, UserOutlined, TeamOutlined, RightOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

// 根据课程名生成稳定的封面渐变色
const COVER_GRADIENTS = [
  'linear-gradient(135deg, #4f6ef7 0%, #22c1c3 100%)',
  'linear-gradient(135deg, #7c6cf7 0%, #4f9df7 100%)',
  'linear-gradient(135deg, #f7706c 0%, #f7a84f 100%)',
  'linear-gradient(135deg, #22b8c3 0%, #3bd07f 100%)',
  'linear-gradient(135deg, #f76fb8 0%, #9a6cf7 100%)',
  'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)',
]

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
      fetchCourses()  // 刷新列表，is_enrolled 会变为 true
    } catch (error) {
      message.error('选课失败')
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-header-text">
          <h1>我的课程</h1>
          <div className="page-subtitle">共 {courses.length} 门课程，点击卡片进入课程详情</div>
        </div>
        {user?.is_teacher && (
          <Button type="primary" icon={<PlusOutlined />} size="large" onClick={() => setCreateModal(true)}>
            创建课程
          </Button>
        )}
      </div>
      <Spin spinning={loading}>
        {!loading && courses.length === 0 ? (
          <Card bordered={false}>
            <Empty
              className="empty-state"
              description={user?.is_teacher ? '还没有课程，点击右上角「创建课程」开始吧' : '暂无可选课程'}
            />
          </Card>
        ) : (
          <Row gutter={[20, 20]}>
            {courses.map((course, idx) => {
              let tagText = '';
              let tagColor = '';
              if (course.teacher_name === user?.username) {
                tagText = '我教的';
                tagColor = 'geekblue';
              } else if (course.is_enrolled) {
                tagText = '我选的';
                tagColor = 'green';
              } else {
                tagText = '未选课';
                tagColor = 'default';
              }

              return (
                <Col xs={24} sm={12} md={8} lg={6} key={course.id}>
                  <Card
                    className="course-card card-hoverable"
                    bordered={false}
                    actions={[
                      <Button type="link" key="detail" onClick={() => navigate(`/courses/${course.id}`)}>
                        查看详情 <RightOutlined style={{ fontSize: 11 }} />
                      </Button>,
                      !user?.is_teacher && !course.is_enrolled && (
                        <Button type="link" key="enroll" icon={<UserAddOutlined />} onClick={() => handleEnroll(course.id)}>选课</Button>
                      )
                    ].filter(Boolean)}
                  >
                    <div className="course-cover" style={{ background: COVER_GRADIENTS[idx % COVER_GRADIENTS.length] }}>
                      <span className="course-code">{course.code}</span>
                      <span className="course-role-tag">
                        <Tag color={tagColor} style={{ marginRight: 0 }}>{tagText}</Tag>
                      </span>
                    </div>
                    <div className="course-info">
                      <h3 title={course.name}>{course.name}</h3>
                      <div className="course-meta">
                        <span className="meta-item"><UserOutlined /> {course.teacher_name}</span>
                        <span className="meta-item"><TeamOutlined /> {course.student_count} 名学生</span>
                      </div>
                    </div>
                  </Card>
                </Col>
              );
            })}
          </Row>
        )}
      </Spin>

      <Modal
        title="创建课程"
        open={createModal}
        onCancel={() => setCreateModal(false)}
        footer={null}
      >
        <Form form={form} onFinish={handleCreate} layout="vertical">
          <Form.Item name="name" label="课程名称" rules={[{ required: true, message: '请输入课程名称' }]}>
            <Input placeholder="例如：Python 程序设计" />
          </Form.Item>
          <Form.Item name="code" label="课程编号" rules={[{ required: true, message: '请输入课程编号' }]}>
            <Input placeholder="例如：CS101" />
          </Form.Item>
          <Form.Item name="description" label="课程描述">
            <Input.TextArea rows={4} placeholder="简要介绍课程内容、目标与要求..." />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block size="large">创建</Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default CourseList
