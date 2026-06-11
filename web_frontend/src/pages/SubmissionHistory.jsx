import { useEffect, useState } from 'react'
import { Table, Spin, message, Tag } from 'antd'
import api from '../api/client'

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
    { title: '作业', dataIndex: 'assignment_title' },
    { title: '提交时间', dataIndex: 'created_at', render: (t) => new Date(t).toLocaleString() },
    { title: '状态', dataIndex: 'status', render: (s) => <Tag color={s === 'success' ? 'green' : 'red'}>{s}</Tag> },
    { title: '得分', dataIndex: 'score', render: (s) => `${s}分` },
  ]

  return (
    <div style={{ padding: 24 }}>
      <h1>我的提交记录</h1>
      <Spin spinning={loading}>
        <Table dataSource={submissions} columns={columns} rowKey="id" />
      </Spin>
    </div>
  )
}

export default SubmissionHistory