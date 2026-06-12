// src/pages/AssignmentList.jsx
import { useEffect, useState } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import {
  Card, Table, Button, Space, Modal, Form, Input, DatePicker,
  message, Popconfirm, Tag, Spin, Divider, Tooltip
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  ExperimentOutlined, ArrowLeftOutlined, MinusCircleOutlined
} from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api/client'

const { TextArea } = Input
const { RangePicker } = DatePicker

const AssignmentList = ({ user }) => {
  const { courseId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [assignments, setAssignments] = useState([])
  const [course, setCourse] = useState(null)
  const [loading, setLoading] = useState(true)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingAssignment, setEditingAssignment] = useState(null)
  const [form] = Form.useForm()

  const isTeacher = user?.is_teacher && course?.teacher === user?.id

  const fetchData = async () => {
    setLoading(true)
    try {
      const courseRes = await api.get(`/courses/${courseId}/`)
      setCourse(courseRes.data)
      const assignRes = await api.get(`/assignments/?course=${courseId}`)
      setAssignments(assignRes.data.results || assignRes.data)
    } catch (error) {
      message.error('加载数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (courseId) fetchData()
  }, [courseId])

  // 自动打开新建弹窗（如果 state 中有 openCreate 标记）
  useEffect(() => {
    if (location.state?.openCreate && isTeacher) {
      openModal()
      // 清除 state，避免刷新后重复打开
      navigate(location.pathname, { replace: true, state: {} })
    }
  }, [location.state, isTeacher])

  const openModal = (record = null) => {
    setEditingAssignment(record)
    if (record) {
      form.setFieldsValue({
        title: record.title,
        description: record.description,
        deadline: dayjs(record.deadline),
        test_cases: record.test_cases && record.test_cases.length > 0
          ? record.test_cases
          : [{ input: '', expected_output: '' }]
      })
    } else {
      form.resetFields()
      form.setFieldsValue({
        test_cases: [{ input: '', expected_output: '' }]
      })
    }
    setModalVisible(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const filteredTestCases = (values.test_cases || []).filter(
        tc => tc.input.trim() !== '' || tc.expected_output.trim() !== ''
      )
      const payload = {
        title: values.title,
        description: values.description,
        deadline: values.deadline.toISOString(),
        course: courseId,
        test_cases: filteredTestCases,
      }
      if (editingAssignment) {
        await api.put(`/assignments/${editingAssignment.id}/`, payload)
        message.success('作业更新成功')
      } else {
        await api.post('/assignments/', payload)
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
        return now.isAfter(deadline)
          ? <Tag color="red">已截止</Tag>
          : <Tag color="green">进行中</Tag>
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
        width={800}
        footer={[
          <Button key="cancel" onClick={() => setModalVisible(false)}>取消</Button>,
          <Button key="submit" type="primary" onClick={handleSubmit}>确定</Button>,
        ]}
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

          <Divider orientation="left">测试用例</Divider>
          <Form.List name="test_cases">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...restField }) => (
                  <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                    <Form.Item
                      {...restField}
                      name={[name, 'input']}
                      label="输入 (stdin)"
                      style={{ width: 250 }}
                    >
                      <Input.TextArea rows={2} placeholder="示例：5\n10" />
                    </Form.Item>
                    <Form.Item
                      {...restField}
                      name={[name, 'expected_output']}
                      label="期望输出"
                      style={{ width: 250 }}
                    >
                      <Input.TextArea rows={2} placeholder="示例：15" />
                    </Form.Item>
                    <MinusCircleOutlined onClick={() => remove(name)} />
                  </Space>
                ))}
                <Form.Item>
                  <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                    添加测试用例
                  </Button>
                </Form.Item>
              </>
            )}
          </Form.List>
          <div style={{ color: '#8c8c8c', fontSize: 12 }}>
            提示：输入/期望输出均为纯文本，评测时会逐字符比对（忽略末尾换行）。
          </div>
        </Form>
      </Modal>
    </div>
  )
}

export default AssignmentList