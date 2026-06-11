import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  Card, Table, Button, Space, Modal, Form, Input, DatePicker, 
  message, Popconfirm, Tag, Spin, Descriptions 
} from 'antd'
import { 
  PlusOutlined, EditOutlined, DeleteOutlined, 
  ExperimentOutlined, ArrowLeftOutlined 
} from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api/client'

const { TextArea } = Input
const { RangePicker } = DatePicker

const AssignmentList = ({ user }) => {
  const { courseId } = useParams()
  const navigate = useNavigate()
  const [assignments, setAssignments] = useState([])
  const [course, setCourse] = useState(null)
  const [loading, setLoading] = useState(true)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingAssignment, setEditingAssignment] = useState(null)
  const [form] = Form.useForm()

  // 是否为当前课程的教师
  const isTeacher = user?.is_teacher && course?.teacher === user?.id

  // 加载课程信息和作业列表
  const fetchData = async () => {
    setLoading(true)
    try {
      // 获取课程详情
      const courseRes = await api.get(`/courses/${courseId}/`)
      setCourse(courseRes.data)
      // 获取作业列表
      const assignRes = await api.get(`/assignments/?course=${courseId}`)
      setAssignments(assignRes.data.results || assignRes.data)
    } catch (error) {
      message.error('加载数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (courseId) {
      fetchData()
    }
  }, [courseId])

  // 打开创建/编辑弹窗
  const openModal = (record = null) => {
    setEditingAssignment(record)
    if (record) {
      form.setFieldsValue({
        title: record.title,
        description: record.description,
        deadline: dayjs(record.deadline),
      })
    } else {
      form.resetFields()
    }
    setModalVisible(true)
  }

  // 提交创建或更新
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const payload = {
        ...values,
        course: courseId,
        deadline: values.deadline.toISOString(),
        // test_cases 可以先给空数组，后续可扩展
        test_cases: [],
      }
      if (editingAssignment) {
        // 更新作业
        await api.put(`/assignments/${editingAssignment.id}/`, payload)
        message.success('作业更新成功')
      } else {
        // 创建作业
        await api.post('/assignments/', payload)
        message.success('作业创建成功')
      }
      setModalVisible(false)
      fetchData() // 刷新列表
    } catch (error) {
      message.error(editingAssignment ? '更新失败' : '创建失败')
    }
  }

  // 删除作业
  const handleDelete = async (id) => {
    try {
      await api.delete(`/assignments/${id}/`)
      message.success('删除成功')
      fetchData()
    } catch (error) {
      message.error('删除失败')
    }
  }

  // 表格列定义
  const columns = [
    {
      title: '作业标题',
      dataIndex: 'title',
      key: 'title',
      render: (text, record) => (
        <a onClick={() => navigate(`/assignments/${record.id}/lab`)}>{text}</a>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '截止时间',
      dataIndex: 'deadline',
      key: 'deadline',
      render: (deadline) => dayjs(deadline).format('YYYY-MM-DD HH:mm:ss'),
      sorter: (a, b) => new Date(a.deadline) - new Date(b.deadline),
    },
    {
      title: '状态',
      key: 'status',
      render: (_, record) => {
        const now = dayjs()
        const deadline = dayjs(record.deadline)
        if (now.isAfter(deadline)) {
          return <Tag color="red">已截止</Tag>
        } else {
          return <Tag color="green">进行中</Tag>
        }
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button 
            type="link" 
            icon={<ExperimentOutlined />}
            onClick={() => navigate(`/assignments/${record.id}/lab`)}
          >
            进入实验
          </Button>
          {isTeacher && (
            <>
              <Button 
                type="link" 
                icon={<EditOutlined />}
                onClick={() => openModal(record)}
              >
                编辑
              </Button>
              <Popconfirm
                title="确定删除该作业吗？"
                onConfirm={() => handleDelete(record.id)}
                okText="确定"
                cancelText="取消"
              >
                <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ]

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <Button 
        icon={<ArrowLeftOutlined />} 
        onClick={() => navigate(`/courses/${courseId}`)}
        style={{ marginBottom: 16 }}
      >
        返回课程
      </Button>
      <Card
        title={
          <Space>
            <span>📋 {course?.name} - 作业列表</span>
            {isTeacher && (
              <Button 
                type="primary" 
                icon={<PlusOutlined />} 
                onClick={() => openModal()}
              >
                新建作业
              </Button>
            )}
          </Space>
        }
        bordered={false}
      >
        <Table 
          columns={columns} 
          dataSource={assignments} 
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* 创建/编辑作业弹窗 */}
      <Modal
        title={editingAssignment ? "编辑作业" : "新建作业"}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setModalVisible(false)}>取消</Button>,
          <Button key="submit" type="primary" onClick={handleSubmit}>确定</Button>,
        ]}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="title"
            label="作业标题"
            rules={[{ required: true, message: '请输入作业标题' }]}
          >
            <Input placeholder="例如：Python 基础练习一" />
          </Form.Item>
          <Form.Item
            name="description"
            label="作业描述"
            rules={[{ required: true, message: '请输入作业描述' }]}
          >
            <TextArea rows={4} placeholder="详细描述作业要求..." />
          </Form.Item>
          <Form.Item
            name="deadline"
            label="截止时间"
            rules={[{ required: true, message: '请选择截止时间' }]}
          >
            <DatePicker showTime format="YYYY-MM-DD HH:mm:ss" style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default AssignmentList