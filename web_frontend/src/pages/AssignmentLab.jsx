// src/pages/AssignmentLab.jsx
import { useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Card, Button, message, Spin, Descriptions, Tabs, Table, Upload, Space, Typography } from 'antd'
import { UploadOutlined, HistoryOutlined, CheckCircleOutlined } from '@ant-design/icons'
import api from '../api/client'

const { TabPane } = Tabs
const { Paragraph } = Typography

const AssignmentLab = ({ user }) => {
  const { assignmentId } = useParams()
  const [assignment, setAssignment] = useState(null)
  const [fileContent, setFileContent] = useState('')
  const [fileName, setFileName] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submissions, setSubmissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploadLoading, setUploadLoading] = useState(false)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const assignRes = await api.get(`/assignments/${assignmentId}/`)
        setAssignment(assignRes.data)
        const subRes = await api.get(`/submissions/?assignment=${assignmentId}`)
        setSubmissions(subRes.data.results || subRes.data)
      } catch (error) {
        message.error('加载作业失败')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [assignmentId])

  const handleSubmit = async () => {
    if (!fileContent.trim()) {
      message.warning('请先上传代码文件')
      return
    }
    setSubmitting(true)
    try {
      await api.post('/submissions/', {
        assignment: assignmentId,
        code: fileContent,
      })
      message.success('提交成功！')
      // 刷新提交记录
      setTimeout(() => {
        fetchSubmissions()
      }, 1000)
      // 清空已上传的文件，以便下次提交新文件
      setFileContent('')
      setFileName('')
    } catch (error) {
      console.error('提交失败:', error)
      message.error(error.response?.data?.detail || '提交失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  const fetchSubmissions = async () => {
    const res = await api.get(`/submissions/?assignment=${assignmentId}`)
    setSubmissions(res.data.results || res.data)
  }

  // 处理文件上传
  const handleFileUpload = (file) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      setFileContent(e.target.result)
      setFileName(file.name)
      message.success(`文件 ${file.name} 加载成功，请点击“提交作业”按钮完成提交`)
      setUploadLoading(false)
    }
    reader.onerror = () => {
      message.error('文件读取失败')
      setUploadLoading(false)
    }
    reader.readAsText(file)
    return false // 阻止自动上传
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

      <Tabs defaultActiveKey="submit">
        <TabPane tab="提交作业" key="submit" icon={<UploadOutlined />}>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Upload
              beforeUpload={handleFileUpload}
              showUploadList={false}
              accept=".py,.java,.c,.cpp,.js,.go,.rs,.txt,.cs,.php,.rb,.pl,.sh"
            >
              <Button icon={<UploadOutlined />} loading={uploadLoading} size="large">
                选择代码文件
              </Button>
            </Upload>
            {fileName && (
              <div style={{ padding: 12, background: '#f6f6f6', borderRadius: 8 }}>
                <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                已加载文件：<strong>{fileName}</strong>
                <Paragraph style={{ marginTop: 8, fontSize: 12, color: '#888' }}>
                  文件内容已准备就绪，点击下方按钮提交。
                </Paragraph>
              </div>
            )}
            <Button
              type="primary"
              onClick={handleSubmit}
              loading={submitting}
              disabled={!fileContent}
              size="large"
              style={{ width: 200 }}
            >
              提交作业
            </Button>
          </Space>
        </TabPane>
        <TabPane tab="提交记录" key="history" icon={<HistoryOutlined />}>
          <Table dataSource={submissions} columns={columns} rowKey="id" pagination={false} />
        </TabPane>
      </Tabs>
    </div>
  )
}

export default AssignmentLab