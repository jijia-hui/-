// src/pages/AssignmentList.jsx
import { useEffect, useState } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import {
  Card, Table, Button, Space, Modal, Form, Input, DatePicker,
  message, Popconfirm, Tag, Spin, Tooltip, Input as AntInput, Upload
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  ExperimentOutlined, ArrowLeftOutlined,
  FileSearchOutlined, SearchOutlined, UploadOutlined
} from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api/client'

const { TextArea } = Input

const AssignmentList = ({ user }) => {
  const { courseId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [assignments, setAssignments] = useState([])
  const [filteredAssignments, setFilteredAssignments] = useState([])
  const [course, setCourse] = useState(null)
  const [loading, setLoading] = useState(true)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingAssignment, setEditingAssignment] = useState(null)
  const [form] = Form.useForm()
  const [searchText, setSearchText] = useState('')

  const isTeacher = user?.is_teacher && course?.teacher === user?.id

  const fetchData = async () => {
    setLoading(true)
    try {
      const courseRes = await api.get(`/courses/${courseId}/`)
      setCourse(courseRes.data)
      const assignRes = await api.get(`/assignments/?course=${courseId}`)
      const data = assignRes.data.results || assignRes.data
      setAssignments(data)
      setFilteredAssignments(data)
    } catch (error) {
      message.error('加载数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (courseId) fetchData()
  }, [courseId])

  useEffect(() => {
    if (location.state?.openCreate && isTeacher) {
      openModal()
      navigate(location.pathname, { replace: true, state: {} })
    }
  }, [location.state, isTeacher])

  useEffect(() => {
    if (!searchText.trim()) {
      setFilteredAssignments(assignments)
    } else {
      const filtered = assignments.filter(assignment =>
        assignment.title.toLowerCase().includes(searchText.toLowerCase()) ||
        assignment.description.toLowerCase().includes(searchText.toLowerCase())
      )
      setFilteredAssignments(filtered)
    }
  }, [searchText, assignments])

  const openModal = (record = null) => {
    setEditingAssignment(record)
    if (record) {
      form.setFieldsValue({
        title: record.title,
        description: record.description,
        deadline: dayjs(record.deadline),
        reference_file: record.reference_file ? [
          { uid: '-1', name: record.reference_file.split('/').pop(), url: record.reference_file }
        ] : []
      })
    } else {
      form.resetFields()
      form.setFieldsValue({ reference_file: [] })
    }
    setModalVisible(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const formData = new FormData()
      formData.append('title', values.title)
      formData.append('description', values.description)
      formData.append('deadline', values.deadline.toISOString())
      formData.append('course', courseId)
      if (values.reference_file && values.reference_file[0]?.originFileObj) {
        formData.append('reference_file', values.reference_file[0].originFileObj)
      }

      if (editingAssignment) {
        await api.put(`/assignments/${editingAssignment.id}/`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        message.success('作业更新成功')
      } else {
        await api.post('/assignments/', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        message.success('作业创建成功')
      }
      setModalVisible(false)
      fetchData()
    } catch (error) {
      message.error(editingAssignment ? '更新失败' : '创建失败')
    }
  }

  const handleDelete = async (id) => {
    try {
      await api.delete(`/assignments/${id}/`)
      message.success('删除成功')
      fetchData()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const columns = [
    {
      title: '作业标题',
      dataIndex: 'title',
      key: 'title',
      width: 200,
      render: (text, record) => (
        <a onClick={() => navigate(`/assignments/${record.id}/lab`)} style={{ fontWeight: 500 }}>
          {text}
        </a>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <span>{text}</span>
        </Tooltip>
      ),
    },
    {
      title: '截止时间',
      dataIndex: 'deadline',
      key: 'deadline',
      width: 180,
      render: (deadline) => dayjs(deadline).format('YYYY-MM-DD HH:mm:ss'),
      sorter: (a, b) => new Date(a.deadline) - new Date(b.deadline),
      defaultSortOrder: 'ascend',
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: (_, record) => {
        const now = dayjs()
        const deadline = dayjs(record.deadline)
        const isExpired = now.isAfter(deadline)
        return (
          <Tag color={isExpired ? 'red' : 'green'} style={{ borderRadius: 16, padding: '0 12px' }}>
            {isExpired ? '已截止' : '进行中'}
          </Tag>
        )
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 340,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="text"
            icon={<ExperimentOutlined />}
            onClick={() => navigate(`/assignments/${record.id}/lab`)}
          >
            进入实验
          </Button>
          {isTeacher && (
            <>
              <Button
                type="text"
                icon={<FileSearchOutlined />}
                onClick={() => navigate(`/assignments/${record.id}/submissions`)}
              >
                查看提交
              </Button>
              <Button
                type="text"
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
                <Button type="text" danger icon={<DeleteOutlined />}>删除</Button>
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
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/courses/${courseId}`)}>
          返回课程
        </Button>

        <Card
          title={
            <Space>
              <span>📋 {course?.name} - 作业列表</span>
              {isTeacher && (
                <Button type="primary" icon={<PlusOutlined />} onClick={() => openModal()}>
                  新建作业
                </Button>
              )}
            </Space>
          }
          bordered={false}
          extra={
            <AntInput
              placeholder="搜索作业标题或描述"
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: 240 }}
              allowClear
            />
          }
        >
          <Table
            columns={columns}
            dataSource={filteredAssignments}
            rowKey="id"
            scroll={{ x: 'max-content' }}
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 条作业`,
            }}
            locale={{ emptyText: '暂无作业，请点击右上角“新建作业”创建' }}
          />
        </Card>

        {/* 创建/编辑作业弹窗 */}
        <Modal
          title={editingAssignment ? "编辑作业" : "新建作业"}
          open={modalVisible}
          onCancel={() => setModalVisible(false)}
          width={600}
          footer={[
            <Button key="cancel" onClick={() => setModalVisible(false)}>取消</Button>,
            <Button key="submit" type="primary" onClick={handleSubmit}>确定</Button>,
          ]}
        >
          <Form form={form} layout="vertical">
            <Form.Item name="title" label="作业标题" rules={[{ required: true, message: '请输入作业标题' }]}>
              <Input placeholder="例如：Python 基础练习一" />
            </Form.Item>
            <Form.Item name="description" label="作业描述" rules={[{ required: true, message: '请输入作业描述' }]}>
              <TextArea rows={4} placeholder="详细描述作业要求..." />
            </Form.Item>
            <Form.Item name="deadline" label="截止时间" rules={[{ required: true, message: '请选择截止时间' }]}>
              <DatePicker showTime format="YYYY-MM-DD HH:mm:ss" style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="reference_file" label="参考文档" valuePropName="fileList" getValueFromEvent={(e) => e?.fileList}>
              <Upload beforeUpload={() => false} maxCount={1} accept=".pdf,.doc,.docx,.jpg,.png,.zip">
                <Button icon={<UploadOutlined />}>选择文件</Button>
              </Upload>
            </Form.Item>
          </Form>
        </Modal>
      </Space>
    </div>
  )
}

export default AssignmentList