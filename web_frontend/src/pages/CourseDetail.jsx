// src/pages/CourseDetail.jsx
import { useParams, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Card, Descriptions, Button, Tabs, List, Spin, message, Tag } from 'antd'
import { BookOutlined, SolutionOutlined } from '@ant-design/icons'
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
    <div style={{ padding: 24 }}>
      <Spin spinning={loading}>
        {course && (
          <>
            <Card title={course.name} style={{ marginBottom: 24 }}>
              <Descriptions column={1}>
                <Descriptions.Item label="课程编号">{course.code}</Descriptions.Item>
                <Descriptions.Item label="授课教师">{course.teacher_name}</Descriptions.Item>
                <Descriptions.Item label="课程描述">{course.description}</Descriptions.Item>
              </Descriptions>
            </Card>

            <Tabs defaultActiveKey="assignments">
              <TabPane tab="作业列表" key="assignments" icon={<BookOutlined />}>
                <List
                  itemLayout="horizontal"
                  dataSource={assignments}
                  renderItem={item => (
                    <List.Item
                      actions={[
                        <Button type="link" onClick={() => navigate(`/assignments/${item.id}/lab`)}>
                          进入实验
                        </Button>
                      ]}
                    >
                      <List.Item.Meta
                        title={item.title}
                        description={`截止时间：${new Date(item.deadline).toLocaleString()}`}
                      />
                    </List.Item>
                  )}
                />
                {isTeacher && (
                  <Button 
                    type="dashed" 
                    block 
                    style={{ marginTop: 16 }} 
                    onClick={() => navigate(`/courses/${courseId}/assignments`, { state: { openCreate: true } })}
                  >
                    新建作业
                  </Button>
                )}
              </TabPane>
              <TabPane tab="学生列表" key="students" icon={<SolutionOutlined />}>
                <List
                  locale={{ emptyText: "暂无学生或您无权查看学生列表" }}
                  dataSource={students}
                  renderItem={stu => (
                    <List.Item>
                      <List.Item.Meta title={stu.username} description={stu.email} />
                    </List.Item>
                  )}
                />
              </TabPane>
            </Tabs>
          </>
        )}
      </Spin>
    </div>
  )
}

export default CourseDetail