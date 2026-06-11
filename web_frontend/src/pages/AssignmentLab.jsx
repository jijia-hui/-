import { useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Card, Button, message, Spin, Descriptions, Alert, Tabs, Table } from 'antd'
import { PlayCircleOutlined, HistoryOutlined } from '@ant-design/icons'
import CodeEditor from '../components/CodeEditor'
import api from '../api/client'

const { TabPane } = Tabs

const AssignmentLab = ({ user }) => {
  const { assignmentId } = useParams()
  const [assignment, setAssignment] = useState(null)
  const [code, setCode] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submissions, setSubmissions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const assignRes = await api.get(`/assignments/${assignmentId}/`)
        setAssignment(assignRes.data)
        // 获取该作业的所有提交记录
        const subRes = await api.get(`/submissions/?assignment=${assignmentId}`)
        setSubmissions(subRes.data.results || subRes.data)
        // 默认代码模板（可以从作业中获取，先留空）
        setCode('# 在此编写代码\n\n')
      } catch (error) {
        message.error('加载作业失败')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [assignmentId])

  const handleSubmit = async () => {
    if (!code.trim()) {
      message.warning('请先编写代码')
      return
    }
    setSubmitting(true)
    try {
      const res = await api.post('/submissions/', {
        assignment: assignmentId,
        code: code,
      })
      message.success('提交成功，正在评测...')
      // 轮询或 WebSocket 获取结果（简化：延迟刷新）
      setTimeout(() => {
        fetchSubmissions()
      }, 3000)
    } catch (error) {
      message.error('提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  const fetchSubmissions = async () => {
    const res = await api.get(`/submissions/?assignment=${assignmentId}`)
    setSubmissions(res.data.results || res.data)
  }

  const columns = [
    { title: '提交时间', dataIndex: 'created_at', render: (t) => new Date(t).toLocaleString() },
    { title: '状态', dataIndex: 'status', render: (s) => {
      const color = s === 'success' ? 'green' : s === 'failed' ? 'red' : 'orange'
      return <span style={{ color }}>{s}</span>
    } },
    { title: '得分', dataIndex: 'score', render: (s) => `${s}分` },
    { title: '输出', dataIndex: 'output', ellipsis: true },
  ]

  if (loading) return <Spin size="large" style={{ margin: 100 }} />

  return (
    <div style={{ padding: 24 }}>
      <Card title={assignment?.title} style={{ marginBottom: 24 }}>
        <Descriptions column={1}>
          <Descriptions.Item label="作业描述">{assignment?.description}</Descriptions.Item>
          <Descriptions.Item label="截止时间">{new Date(assignment?.deadline).toLocaleString()}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Tabs defaultActiveKey="editor">
        <TabPane tab="代码编辑" key="editor" icon={<PlayCircleOutlined />}>
          <CodeEditor value={code} onChange={setCode} />
          <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleSubmit} loading={submitting} style={{ marginTop: 16 }}>
            提交评测
          </Button>
        </TabPane>
        <TabPane tab="提交记录" key="history" icon={<HistoryOutlined />}>
          <Table dataSource={submissions} columns={columns} rowKey="id" pagination={false} />
        </TabPane>
      </Tabs>
    </div>
  )
}

export default AssignmentLab