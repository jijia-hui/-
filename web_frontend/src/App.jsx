import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import PrivateRoute from './components/PrivateRoute'
import Login from './pages/Login'
import Register from './pages/Register'
import CourseList from './pages/CourseList'
import CourseDetail from './pages/CourseDetail'
import AssignmentList from './pages/AssignmentList'
import AssignmentLab from './pages/AssignmentLab'
import SubmissionHistory from './pages/SubmissionHistory'
import Profile from './pages/Profile'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState(null)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    const userStr = localStorage.getItem('user')
    if (token && userStr) {
      setIsAuthenticated(true)
      setUser(JSON.parse(userStr))
    }
  }, [])

  const login = (userData, token) => {
    localStorage.setItem('access_token', token)
    localStorage.setItem('user', JSON.stringify(userData))
    setIsAuthenticated(true)
    setUser(userData)
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    setIsAuthenticated(false)
    setUser(null)
  }

  return (
    <>
      <Navbar isAuthenticated={isAuthenticated} user={user} logout={logout} />
      <Routes>
        <Route path="/login" element={<Login onLogin={login} />} />
        <Route path="/register" element={<Register />} />
        <Route path="/" element={<Navigate to="/courses" />} />
        {/* 注意：下面这行重复的路由已删除，只保留 PrivateRoute 内部的 */}
        <Route element={<PrivateRoute isAuthenticated={isAuthenticated} />}>
          <Route path="/courses" element={<CourseList user={user} />} />
          <Route path="/courses/:courseId" element={<CourseDetail user={user} />} />
          <Route path="/courses/:courseId/assignments" element={<AssignmentList user={user} />} />
          <Route path="/assignments/:assignmentId/lab" element={<AssignmentLab user={user} />} />
          <Route path="/submissions" element={<SubmissionHistory user={user} />} />
          <Route path="/profile" element={<Profile user={user} />} />
        </Route>
      </Routes>
    </>
  )
}

export default App