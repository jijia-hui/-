// src/pages/CourseDetail.jsx
import { useParams, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Card, Button, Tabs, List, Spin, message, Tag, Avatar, Empty } from 'antd'
import { BookOutlined, SolutionOutlined, UserOutlined, ClockCircleOutlined, RightOutlined, PlusOutlined } from '@ant-design/icons'
import api from '../api/client'

const { TabPane } = Tabs

const CourseDetail = ({ user }) => {
  const { courseId } = useParams()
  const [course, setCourse] = useState(null)
  const [assignments, setAssignments] = useState([])
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    const fetchData = async () => {
      try {
        const courseRes = await api.get(`/courses/${courseId}/`)
        setCourse(courseRes.data)
        const assignRes = await api.get(`/assignments/?course=${courseId}`)
        setAssignments(assignRes.data.results || assignRes.data)
        setStudents(courseRes.data.students || [])
      } catch (error) {
        message.error('加载课程详情失败')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [courseId])

  const isTeacher = user?.is_teacher && course?.teacher === user?.id

  return (
    <div className="page-container">
      <Spin spinning={loading}>
        {course && (
          <>
            <div className="detail-banner">
              <Tag style={{ background: 'rgba(255,255,255,0.2)', border: '1px solid rgba(255,255,255,0.35)', color: '#fff', marginBottom: 12 }}>
                {course.code}
              </Tag>
              <h1>{course.name}</h1>
              <div className="banner-sub">
                <span><UserOutlined /> 授课教师：{course.teacher_name}</span>
                <span><SolutionOutlined /> {students.length} 名学生</span>
                <span><BookOutlined /> {assignments.length} 个作业</span>
              </div>
              {course.description && (
                <p style={{ marginTop: 14, marginBottom: 0, color: 'rgba(255,255,255,0.9)', fontSize: 14, maxWidth: 720 }}>
                  {course.description}
                </p>
              )}
            </div>

            <Card bordered={false}>
              <Tabs defaultActiveKey="assignments" size="large">
                <TabPane tab={<span><BookOutlined /> 作业列表</span>} key="assignments">
                  <List
                    itemLayout="horizontal"
                    dataSource={assignments}
                    locale={{ emptyText: <Empty className="empty-state" description="暂无作业" /> }}
                    renderItem={item => {
                      const expired = new Date() > new Date(item.deadline)
                      return (
                        <List.Item
                          style={{ borderRadius: 12, padding: '16px 12px', transition: 'background 0.2s' }}
                          actions={[
                            <Button type="primary" ghost key="enter" onClick={() => navigate(`/assignments/${item.id}/lab`)}>
                              进入作业 <RightOutlined style={{ fontSize: 11 }} />
                            </Button>
                          ]}
                        >
                          <List.Item.Meta
                            avatar={
                              <Avatar
                                shape="square"
                                size={44}
                                style={{ borderRadius: 10, background: expired ? '#f1f2f6' : 'linear-gradient(135deg, #4f6ef7 0%, #22c1c3 100%)' }}
                                icon={<BookOutlined style={{ color: expired ? '#9aa3b8' : '#fff' }} />}
                              />
                            }
                            title={<span style={{ fontWeight: 600 }}>{item.title}</span>}
                            description={
                              <span style={{ color: expired ? '#ff4d4f' : '#6b7280' }}>
                                <ClockCircleOutlined /> 截止时间：{new Date(item.deadline).toLocaleString()}
                                {expired && <Tag color="red" style={{ marginLeft: 8 }}>已截止</Tag>}
                              </span>
                            }
                          />
                        </List.Item>
                      )
                    }}
                  />
                  {isTeacher && (
                    <Button
                      type="dashed"
                      block
                      icon={<PlusOutlined />}
                      size="large"
                      style={{ marginTop: 16, borderRadius: 12, height: 48 }}
                      onClick={() => navigate(`/courses/${courseId}/assignments`, { state: { openCreate: true } })}
                    >
                      新建作业
                    </Button>
                  )}
                </TabPane>
                <TabPane tab={<span><SolutionOutlined /> 学生列表</span>} key="students">
                  <List
                    locale={{ emptyText: <Empty className="empty-state" description="暂无学生或您无权查看学生列表" /> }}
                    dataSource={students}
                    renderItem={stu => (
                      <List.Item>
                        <List.Item.Meta
                          avatar={
                            <Avatar style={{ background: 'linear-gradient(135deg, #7c6cf7 0%, #4f9df7 100%)' }} icon={<UserOutlined />} />
                          }
                          title={stu.username}
                          description={stu.email}
                        />
                      </List.Item>
                    )}
                  />
                </TabPane>
              </Tabs>
            </Card>
          </>
        )}
      </Spin>
    </div>
  )
}

export default CourseDetail
