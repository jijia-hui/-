// src/pages/AssignmentLab.jsx
import { useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import {
  Card, Button, message, Spin, Descriptions, Tabs, Table, Upload, Space, Typography, Modal, InputNumber, Tag, Empty
} from 'antd'
import {
  UploadOutlined, HistoryOutlined, CheckCircleOutlined, EyeOutlined, SaveOutlined,
  InboxOutlined, ClockCircleOutlined, FileTextOutlined
} from '@ant-design/icons'
import api from '../api/client'

const { TabPane } = Tabs
const { Paragraph, Text } = Typography

const STATUS_MAP = {
  graded: { color: 'green', label: '已评分' },
  pending: { color: 'orange', label: '待评分' },
}

const StatusTag = ({ status }) => {
  const conf = STATUS_MAP[status] || { color: 'default', label: status }
  return <Tag color={conf.color}>{conf.label}</Tag>
}

const AssignmentLab = ({ user }) => {
  const { assignmentId } = useParams()
  const [assignment, setAssignment] = useState(null)
  const [fileContent, setFileContent] = useState('')
  const [fileName, setFileName] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submissions, setSubmissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploadLoading, setUploadLoading] = useState(false)
  const [detailVisible, setDetailVisible] = useState(false)
  const [selectedSubmission, setSelectedSubmission] = useState(null)
  const [scoreValue, setScoreValue] = useState(0)
  const [submittingGrade, setSubmittingGrade] = useState(false)

  const isTeacher = user?.is_teacher || false

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
      message.warning('请先上传文件')
      return
    }
    setSubmitting(true)
    try {
      await api.post('/submissions/', {
        assignment: assignmentId,
        code: fileContent,
      })
      message.success('提交成功！')
      setTimeout(() => fetchSubmissions(), 1000)
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

  const handleFileUpload = (file) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      setFileContent(e.target.result)
      setFileName(file.name)
      message.success(`文件 ${file.name} 加载成功，请点击“提交作业”按钮完成提交`)
      setUploadLoading(false)
    }
    reader.onerror = () => {
      message.error('文件读取失败，请确保文件为文本格式（.txt, .md, .py等）')
      setUploadLoading(false)
    }
    reader.readAsText(file)
    return false
  }

  const studentColumns = [
    { title: '提交时间', dataIndex: 'created_at', render: (t) => new Date(t).toLocaleString() },
    { title: '状态', dataIndex: 'status', render: (s) => <StatusTag status={s} /> },
    { title: '得分', dataIndex: 'score', render: (s) => <Text strong style={{ color: '#4f6ef7' }}>{s} 分</Text> },
  ]

  const teacherColumns = [
    { title: '学生', dataIndex: 'student_name', key: 'student_name' },
    { title: '提交时间', dataIndex: 'created_at', render: (t) => new Date(t).toLocaleString() },
    { title: '状态', dataIndex: 'status', render: (s) => <StatusTag status={s} /> },
    { title: '得分', dataIndex: 'score', render: (s) => <Text strong style={{ color: '#4f6ef7' }}>{s} 分</Text> },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => {
            setSelectedSubmission(record)
            setScoreValue(record.score)
            setDetailVisible(true)
          }}
        >
          评分/详情
        </Button>
      ),
    },
  ]

  const handleSaveGrade = async () => {
    if (!selectedSubmission) return
    setSubmittingGrade(true)
    try {
      await api.post(`/submissions/${selectedSubmission.id}/grade/`, { score: scoreValue })
      message.success('评分已保存')
      setDetailVisible(false)
      const subRes = await api.get(`/submissions/?assignment=${assignmentId}`)
      setSubmissions(subRes.data.results || subRes.data)
    } catch (error) {
      console.error('评分失败:', error.response?.data)
      message.error(error.response?.data?.detail || '保存失败')
    } finally {
      setSubmittingGrade(false)
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 120 }}>
        <Spin size="large" />
      </div>
    )
  }

  const expired = assignment && new Date() > new Date(assignment.deadline)

  return (
    <div className="page-container">
      <Card bordered={false} style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <Space size="middle" align="center">
              <span className="brand-icon-box"><FileTextOutlined /></span>
              <h1 style={{ margin: 0, fontSize: 22 }}>{assignment?.title}</h1>
              {expired ? <Tag color="red">已截止</Tag> : <Tag color="green">进行中</Tag>}
            </Space>
            <Paragraph style={{ marginTop: 16, fontSize: 15, color: '#3c4356', maxWidth: 760 }}>
              {assignment?.description}
            </Paragraph>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ color: '#6b7280', fontSize: 13, marginBottom: 4 }}>
              <ClockCircleOutlined /> 截止时间
            </div>
            <Text strong style={{ color: expired ? '#ff4d4f' : '#1f2430', fontSize: 16 }}>
              {new Date(assignment?.deadline).toLocaleString()}
            </Text>
            {assignment?.reference_file && (
              <div style={{ marginTop: 10 }}>
                <Button type="link" href={assignment.reference_file} target="_blank" download style={{ padding: 0 }}>
                  📎 下载参考文档
                </Button>
              </div>
            )}
          </div>
        </div>
      </Card>

      <Card bordered={false}>
        <Tabs defaultActiveKey={isTeacher ? "history" : "submit"} size="large">
          {!isTeacher && (
            <TabPane tab={<span><UploadOutlined /> 提交作业</span>} key="submit">
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <Upload
                  beforeUpload={handleFileUpload}
                  showUploadList={false}
                  accept=".txt,.md,.markdown,.py,.java,.c,.cpp,.js,.go,.rs,.cs,.php,.rb,.pl,.sh,.json,.xml,.html,.css"
                >
                  <div className="upload-dropzone">
                    <span className="dz-icon"><InboxOutlined /></span>
                    <span className="dz-title">点击选择文件上传</span>
                    <span className="dz-hint">
                      支持文本格式文件（.txt, .md, .py, .java, .c, .js 等），文件内容将作为答案提交
                    </span>
                  </div>
                </Upload>
                {fileName && (
                  <div className="file-ready-box">
                    <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
                    <div>
                      <Text strong>已加载文件：{fileName}</Text>
                      <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>
                        文件内容已准备就绪，点击下方按钮提交
                      </div>
                    </div>
                  </div>
                )}
                <Button
                  type="primary"
                  onClick={handleSubmit}
                  loading={submitting || uploadLoading}
                  disabled={!fileContent}
                  size="large"
                  icon={<UploadOutlined />}
                  style={{ width: 220, height: 46, borderRadius: 23 }}
                >
                  提交作业
                </Button>
              </Space>
            </TabPane>
          )}

          <TabPane tab={<span><HistoryOutlined /> 提交记录</span>} key="history">
            {submissions.length === 0 ? (
              <Empty
                className="empty-state"
                description={isTeacher ? '还没有学生提交作业' : '您还没有提交过作业，请上传文件后提交'}
              />
            ) : (
              <Table
                dataSource={submissions}
                columns={isTeacher ? teacherColumns : studentColumns}
                rowKey="id"
                pagination={{ pageSize: 8 }}
              />
            )}
          </TabPane>
        </Tabs>
      </Card>

      <Modal
        title="评分与详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={800}
      >
        {selectedSubmission && (
          <>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="学生">{selectedSubmission.student_name}</Descriptions.Item>
              <Descriptions.Item label="提交时间">{new Date(selectedSubmission.created_at).toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="状态"><StatusTag status={selectedSubmission.status} /></Descriptions.Item>
              <Descriptions.Item label="当前得分">
                <Text strong style={{ color: '#4f6ef7' }}>{selectedSubmission.score} 分</Text>
              </Descriptions.Item>
            </Descriptions>
            <div style={{ marginTop: 20 }}>
              <Text strong>提交的答案：</Text>
              <pre className="code-view" style={{ marginTop: 8 }}>
                {selectedSubmission.code}
              </pre>
            </div>
            {selectedSubmission.output && (
              <div style={{ marginTop: 16 }}>
                <Text strong>系统输出：</Text>
                <pre className="code-view" style={{ marginTop: 8, maxHeight: 240 }}>
                  {selectedSubmission.output}
                </pre>
              </div>
            )}
            {isTeacher && (
              <div style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid #f0f0f0' }}>
                <Text strong>教师评分（0-100）：</Text>
                <Space style={{ marginTop: 8 }}>
                  <InputNumber
                    min={0}
                    max={100}
                    value={scoreValue}
                    onChange={(val) => setScoreValue(val)}
                    style={{ width: 120 }}
                    size="large"
                  />
                  <Button type="primary" icon={<SaveOutlined />} onClick={handleSaveGrade} loading={submittingGrade} size="large">
                    保存分数
                  </Button>
                </Space>
              </div>
            )}
          </>
        )}
      </Modal>
    </div>
  )
}

export default AssignmentLab
