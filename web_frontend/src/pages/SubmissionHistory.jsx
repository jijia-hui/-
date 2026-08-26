import { useEffect, useState } from 'react'
import { Table, Spin, message, Tag, Card, Typography, Empty } from 'antd'
import api from '../api/client'

const { Text } = Typography

const STATUS_MAP = {
  graded: { color: 'green', label: '已评分' },
  pending: { color: 'orange', label: '待评分' },
}

const SubmissionHistory = () => {
  const [submissions, setSubmissions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchSubmissions = async () => {
      try {
        const res = await api.get('/submissions/')
        setSubmissions(res.data.results || res.data)
      } catch (error) {
        message.error('加载提交记录失败')
      } finally {
        setLoading(false)
      }
    }
    fetchSubmissions()
  }, [])

  const columns = [
    { title: '作业', dataIndex: 'assignment_title', render: (t) => <Text strong>{t}</Text> },
    { title: '提交时间', dataIndex: 'created_at', render: (t) => new Date(t).toLocaleString() },
    {
      title: '状态',
      dataIndex: 'status',
      render: (s) => {
        const conf = STATUS_MAP[s] || { color: 'default', label: s }
        return <Tag color={conf.color}>{conf.label}</Tag>
      },
    },
    {
      title: '得分',
      dataIndex: 'score',
      render: (s) => <Text strong style={{ color: '#4f6ef7' }}>{s} 分</Text>,
    },
  ]

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-header-text">
          <h1>我的提交记录</h1>
          <div className="page-subtitle">共 {submissions.length} 条提交记录</div>
        </div>
      </div>
      <Card bordered={false}>
        <Spin spinning={loading}>
          <Table
            dataSource={submissions}
            columns={columns}
            rowKey="id"
            pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
            locale={{ emptyText: <Empty className="empty-state" description="暂无提交记录" /> }}
          />
        </Spin>
      </Card>
    </div>
  )
}

export default SubmissionHistory
