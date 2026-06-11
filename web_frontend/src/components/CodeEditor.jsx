import Editor from '@monaco-editor/react'

const CodeEditor = ({ language = 'python', value, onChange, height = '500px' }) => {
  return (
    <Editor
      height={height}
      language={language}
      value={value}
      onChange={onChange}
      theme="vs-dark"
      options={{
        minimap: { enabled: false },
        fontSize: 14,
        automaticLayout: true,
      }}
    />
  )
}

export default CodeEditor