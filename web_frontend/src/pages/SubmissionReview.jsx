// src/pages/SubmissionReview.jsx
import { useParams, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Card, Table, Button, Spin, message, Tag, Space, Modal, Typography, Descriptions, InputNumber } from 'antd'
import { ArrowLeftOutlined, EyeOutlined, SaveOutlined } from '@ant-design/icons'
import api from '../api/client'

const { Text } = Typography

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

  const columns = [
    { title: '学生', dataIndex: 'student_name', key: 'student_name' },
    { title: '提交时间', dataIndex: 'created_at', render: (t) => new Date(t).toLocaleString() },
    { title: '状态', dataIndex: 'status', render: (s) => <Tag color={s === 'graded' ? 'green' : 'orange'}>{s}</Tag> },
    { title: '得分', dataIndex: 'score', render: (s) => `${s}分` },
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
    <div style={{ padding: 24 }}>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>
        返回
      </Button>
      <Card title={`作业提交记录 - ${assignment?.title || '加载中...'}`}>
        <Spin spinning={loading}>
          <Table dataSource={submissions} columns={columns} rowKey="id" pagination={{ pageSize: 10 }} />
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
              <Descriptions.Item label="状态">
                <Tag color={selectedSubmission.status === 'graded' ? 'green' : 'orange'}>{selectedSubmission.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="当前得分">
                {selectedSubmission.score}分
              </Descriptions.Item>
            </Descriptions>
            <div style={{ marginTop: 16 }}>
              <Text strong>提交的代码：</Text>
              <pre style={{ background: '#f6f6f6', padding: 12, borderRadius: 8, overflow: 'auto', maxHeight: 300 }}>
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
            <div style={{ marginTop: 24 }}>
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
          </>
        )}
      </Modal>
    </div>
  )
}

export default SubmissionReview