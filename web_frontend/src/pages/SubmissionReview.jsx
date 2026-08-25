// src/pages/SubmissionReview.jsx
import { useParams, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Card, Table, Button, Spin, message, Tag, Space, Modal, Typography, Descriptions, InputNumber, Empty } from 'antd'
import { ArrowLeftOutlined, EyeOutlined, SaveOutlined } from '@ant-design/icons'
import api from '../api/client'

const { Text } = Typography

const StatusTag = ({ status }) => (
  <Tag color={status === 'graded' ? 'green' : 'orange'}>
    {status === 'graded' ? '已评分' : '待评分'}
  </Tag>
)

const SubmissionReview = () => {
  const { assignmentId } = useParams()
  const navigate = useNavigate()
  const [submissions, setSubmissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [assignment, setAssignment] = useState(null)
  const [detailVisible, setDetailVisible] = useState(false)
  const [selectedSubmission, setSelectedSubmission] = useState(null)
  const [scoreValue, setScoreValue] = useState(0)
  const [submittingGrade, setSubmittingGrade] = useState(false)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const assignRes = await api.get(`/assignments/${assignmentId}/`)
        setAssignment(assignRes.data)
        const subRes = await api.get(`/submissions/?assignment=${assignmentId}`)
        setSubmissions(subRes.data.results || subRes.data)
      } catch (error) {
        message.error('加载数据失败')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [assignmentId])

  const openDetail = (record) => {
    setSelectedSubmission(record)
    setScoreValue(record.score)
    setDetailVisible(true)
  }

  const handleSaveGrade = async () => {
    if (!selectedSubmission) return
    setSubmittingGrade(true)
    try {
      await api.post(`/submissions/${selectedSubmission.id}/grade/`, { score: scoreValue })
      message.success('评分已保存')
      setDetailVisible(false)
      // 刷新列表
      const subRes = await api.get(`/submissions/?assignment=${assignmentId}`)
      setSubmissions(subRes.data.results || subRes.data)
    } catch (error) {
      message.error(error.response?.data?.detail || '保存失败')
    } finally {
      setSubmittingGrade(false)
    }
  }

  const gradedCount = submissions.filter(s => s.status === 'graded').length

  const columns = [
    { title: '学生', dataIndex: 'student_name', key: 'student_name', render: (t) => <Text strong>{t}</Text> },
    { title: '提交时间', dataIndex: 'created_at', render: (t) => new Date(t).toLocaleString() },
    { title: '状态', dataIndex: 'status', render: (s) => <StatusTag status={s} /> },
    { title: '得分', dataIndex: 'score', render: (s) => <Text strong style={{ color: '#4f6ef7' }}>{s} 分</Text> },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Button type="link" icon={<EyeOutlined />} onClick={() => openDetail(record)}>
          评分/查看
        </Button>
      ),
    },
  ]

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-header-text">
          <h1>作业提交批改</h1>
          <div className="page-subtitle">
            {assignment?.title || '加载中...'} · 共 {submissions.length} 份提交，已批改 {gradedCount} 份
          </div>
        </div>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
          返回
        </Button>
      </div>
      <Card bordered={false}>
        <Spin spinning={loading}>
          <Table
            dataSource={submissions}
            columns={columns}
            rowKey="id"
            pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 份提交` }}
            locale={{ emptyText: <Empty className="empty-state" description="暂无学生提交" /> }}
          />
        </Spin>
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
              <Text strong>提交的代码：</Text>
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
          </>
        )}
      </Modal>
    </div>
  )
}

export default SubmissionReview
