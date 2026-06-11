web_backend文件结构
D:.
│  create_tokens.py
│  manage.py
│  
├─apps
│  │  admin.py
│  │  apps.py
│  │  models.py
│  │  permissions.py
│  │  serializers.py
│  │  tasks.py
│  │  tests.py
│  │  urls.py
│  │  views.py
│  │  __init__.py
│  │  
│  ├─migrations
│  │  │  0001_initial.py
│  │  │  __init__.py
│  │  │  
│  │  └─__pycache__
│  │          0001_initial.cpython-312.pyc
│  │          __init__.cpython-312.pyc
│  │          
│  └─__pycache__
│          admin.cpython-312.pyc
│          apps.cpython-312.pyc
│          models.cpython-312.pyc
│          permissions.cpython-312.pyc
│          serializers.cpython-312.pyc
│          urls.cpython-312.pyc
│          views.cpython-312.pyc
│          __init__.cpython-312.pyc
│          
└─web_backend
    │  asgi.py
    │  celery.py
    │  settings.py
    │  urls.py
    │  wsgi.py
    │  __init__.py
    │  
    └─__pycache__
            celery.cpython-312.pyc
            settings.cpython-312.pyc
            urls.cpython-312.pyc
            wsgi.cpython-312.pyc
            __init__.cpython-312.pyc
            
web_frontend文件结构：
D:.
│  .eslintrc.cjs
|  index.html
|  package-lock.json
|  package.json
|  vite.config.js
├─node_modules
└─src
src目录结构：
D:.
│  App.jsx
│  main.jsx
│  
├─api
│      client.js
│      
├─components
│      CodeEditor.jsx
│      Navbar.jsx
│      PrivateRoute.jsx
│      
├─pages
│      AssignmentLab.jsx
│      AssignmentList.jsx
│      CourseDetail.jsx
│      CourseList.jsx
│      Login.jsx
│      Profile.jsx
│      Register.jsx
│      SubmissionHistory.jsx
│      
└─styles
        global.css