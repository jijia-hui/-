import { useEffect, useState } from 'react'
import { Card, Row, Col, Button, Spin, message, Tag, Modal, Form, Input, Empty, Popconfirm } from 'antd'
import { PlusOutlined, UserAddOutlined, UserDeleteOutlined, UserOutlined, TeamOutlined, RightOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
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
  const [editingCourse, setEditingCourse] = useState(null)
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

  const openCreateModal = () => {
    setEditingCourse(null)
    form.resetFields()
    setCreateModal(true)
  }

  const openEditModal = (course) => {
    setEditingCourse(course)
    form.setFieldsValue({
      name: course.name,
      code: course.code,
      description: course.description,
    })
    setCreateModal(true)
  }

  const handleSubmit = async (values) => {
    try {
      if (editingCourse) {
        await api.patch(`/courses/${editingCourse.id}/`, values)
        message.success('课程更新成功')
      } else {
        await api.post('/courses/', values)
        message.success('课程创建成功')
      }
      setCreateModal(false)
      setEditingCourse(null)
      form.resetFields()
      fetchCourses()
    } catch (error) {
      message.error(editingCourse ? '更新失败' : '创建失败')
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

  const handleUnenroll = async (courseId) => {
    try {
      await api.post(`/courses/${courseId}/unenroll/`)
      message.success('退课成功')
      fetchCourses()  // 刷新列表，is_enrolled 会变为 false
    } catch (error) {
      message.error('退课失败')
    }
  }

  const handleDelete = async (courseId) => {
    try {
      await api.delete(`/courses/${courseId}/`)
      message.success('课程删除成功')
      fetchCourses()
    } catch (error) {
      message.error('删除失败')
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
          <Button type="primary" icon={<PlusOutlined />} size="large" onClick={openCreateModal}>
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
                      ),
                      !user?.is_teacher && course.is_enrolled && (
                        <Popconfirm key="unenroll" title="确定退选该课程吗？" onConfirm={() => handleUnenroll(course.id)} okText="确定" cancelText="取消">
                          <Button type="link" danger icon={<UserDeleteOutlined />}>退课</Button>
                        </Popconfirm>
                      ),
                      course.teacher_name === user?.username && (
                        <Button type="link" key="edit" icon={<EditOutlined />} onClick={() => openEditModal(course)}>编辑</Button>
                      ),
                      course.teacher_name === user?.username && (
                        <Popconfirm key="delete" title="确定删除该课程吗？其下作业与提交将一并删除" onConfirm={() => handleDelete(course.id)} okText="确定" cancelText="取消">
                          <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
                        </Popconfirm>
                      ),
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
        title={editingCourse ? '编辑课程' : '创建课程'}
        open={createModal}
        onCancel={() => {
          setCreateModal(false)
          setEditingCourse(null)
        }}
        footer={null}
      >
        <Form form={form} onFinish={handleSubmit} layout="vertical">
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
            <Button type="primary" htmlType="submit" block size="large">
              {editingCourse ? '保存' : '创建'}
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default CourseList
