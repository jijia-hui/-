// src/pages/AssignmentLab.jsx (完整，已添加参考文档下载)
import { useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import {
  Card, Button, message, Spin, Descriptions, Tabs, Table, Upload, Space, Typography, Alert, Modal, InputNumber
} from 'antd'
import {
  UploadOutlined, HistoryOutlined, CheckCircleOutlined, EyeOutlined, SaveOutlined
} from '@ant-design/icons'
import api from '../api/client'

const { TabPane } = Tabs
const { Title, Paragraph, Text } = Typography

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
      message.error('文件读取失败')
      setUploadLoading(false)
    }
    reader.readAsText(file)
    return false
  }

  const studentColumns = [
    { title: '提交时间', dataIndex: 'created_at', render: (t) => new Date(t).toLocaleString() },
    { title: '状态', dataIndex: 'status', render: (s) => {
      const color = s === 'graded' ? 'green' : s === 'pending' ? 'orange' : 'red'
      const label = s === 'graded' ? '已评分' : s === 'pending' ? '待评分' : s
      return <span style={{ color }}>{label}</span>
    } },
    { title: '得分', dataIndex: 'score', render: (s) => `${s}分` },
  ]

  const teacherColumns = [
    { title: '学生', dataIndex: 'student_name', key: 'student_name' },
    { title: '提交时间', dataIndex: 'created_at', render: (t) => new Date(t).toLocaleString() },
    { title: '状态', dataIndex: 'status', render: (s) => {
      const color = s === 'graded' ? 'green' : s === 'pending' ? 'orange' : 'red'
      const label = s === 'graded' ? '已评分' : s === 'pending' ? '待评分' : s
      return <span style={{ color }}>{label}</span>
    } },
    { title: '得分', dataIndex: 'score', render: (s) => `${s}分` },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
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
        </Space>
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

  if (loading) return <Spin size="large" style={{ margin: 100 }} />

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <Card style={{ borderRadius: 12, marginBottom: 24 }} bodyStyle={{ padding: '24px' }}>
        <Title level={3}>{assignment?.title}</Title>
        <Descriptions column={1} style={{ marginTop: 16 }}>
          <Descriptions.Item label="作业描述">
            <Paragraph style={{ fontSize: 16 }}>{assignment?.description}</Paragraph>
          </Descriptions.Item>
          <Descriptions.Item label="截止时间">
            <Text strong style={{ color: '#ff4d4f' }}>{new Date(assignment?.deadline).toLocaleString()}</Text>
          </Descriptions.Item>
        </Descriptions>
        {/* 参考文档下载按钮 */}
        {assignment?.reference_file && (
          <div style={{ marginTop: 16 }}>
            <Button type="link" href={assignment.reference_file} target="_blank" download>
              📎 下载参考文档
            </Button>
          </div>
        )}
      </Card>

      <Tabs defaultActiveKey={isTeacher ? "history" : "submit"} size="large">
        {!isTeacher && (
          <TabPane tab={<span><UploadOutlined /> 提交作业</span>} key="submit">
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
                <div style={{ padding: 16, background: '#f6ffed', borderRadius: 8, border: '1px solid #b7eb8f' }}>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  <Text strong>已加载文件：{fileName}</Text>
                  <Paragraph style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
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
        )}

        <TabPane tab={<span><HistoryOutlined /> 提交记录</span>} key="history">
          {submissions.length === 0 ? (
            <Alert
              message="暂无提交记录"
              description={isTeacher ? "还没有学生提交作业。" : "您还没有提交过作业，请上传文件后提交。"}
              type="info"
              showIcon
              style={{ marginTop: 16 }}
            />
          ) : (
            <Table
              dataSource={submissions}
              columns={isTeacher ? teacherColumns : studentColumns}
              rowKey="id"
              pagination={{ pageSize: 8 }}
              style={{ marginTop: 16 }}
            />
          )}
        </TabPane>
      </Tabs>

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
              <Descriptions.Item label="状态">
                <span style={{ color: selectedSubmission.status === 'graded' ? 'green' : 'orange' }}>
                  {selectedSubmission.status === 'graded' ? '已评分' : '待评分'}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="当前得分">{selectedSubmission.score}分</Descriptions.Item>
            </Descriptions>
            <div style={{ marginTop: 16 }}>
              <Text strong>提交的代码：</Text>
              <pre style={{ background: '#f6f6f6', padding: 12, borderRadius: 8, overflow: 'auto', maxHeight: 400 }}>
                {selectedSubmission.code}
              </pre>
            </div>
            {selectedSubmission.output && (
              <div style={{ marginTop: 16 }}>
                <Text strong>系统输出：</Text>
                <pre style={{ background: '#f6f6f6', padding: 12, borderRadius: 8, overflow: 'auto' }}>
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
                  />
                  <Button type="primary" icon={<SaveOutlined />} onClick={handleSaveGrade} loading={submittingGrade}>
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